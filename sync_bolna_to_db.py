"""
Fetch ALL real call executions from Bolna AI and sync into aria_calls.db
"""
import os, sys, json, sqlite3, requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Force UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

load_dotenv(Path(__file__).parent / ".env")

BOLNA_API_KEY  = os.getenv("BOLNA_API_KEY", "")
BOLNA_AGENT_ID = os.getenv("BOLNA_AGENT_ID", "")
API_URL        = "https://api.bolna.dev"

headers = {"Authorization": f"Bearer {BOLNA_API_KEY}"}

# ── Step 1: Fetch all executions (paginate if needed) ────────────────────────
print("Fetching real call executions from Bolna...")

all_calls = []
page = 1
while True:
    resp = requests.get(
        f"{API_URL}/v1/agent/{BOLNA_AGENT_ID}/executions",
        headers=headers,
        params={"page_number": page, "page_size": 50},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()

    if isinstance(data, list):
        all_calls.extend(data)
        break                          # v1 returns a flat list
    else:
        chunk = data.get("data", [])
        all_calls.extend(chunk)
        if not data.get("has_more"):
            break
        page += 1

print(f"Total calls fetched from Bolna: {len(all_calls)}")

# ── Step 2: Show all calls clearly ──────────────────────────────────────────
for i, c in enumerate(all_calls, 1):
    call_id   = c.get("id", "?")
    status    = c.get("call_status") or c.get("status", "?")
    duration  = c.get("conversation_duration") or c.get("duration", 0)
    phone     = c.get("to_number") or c.get("recipient_phone_number") or c.get("phone_number", "unknown")
    started   = c.get("created_at") or c.get("started_at", "")
    cost      = c.get("total_cost", 0)
    transcript_raw = c.get("transcript", "")
    transcript_len = len(transcript_raw) if transcript_raw else 0

    print(f"\n[{i:02d}] ID={call_id}")
    print(f"      Status={status}  Duration={duration}s  Phone={phone}")
    print(f"      Started={started}  Cost=${cost}")
    print(f"      Transcript chars: {transcript_len}")

# ── Step 3: Sync into aria_calls.db (call_records table) ────────────────────
print("\n\nSyncing to aria_calls.db ...")

DB_PATH = str(Path(__file__).parent / "aria_calls.db")
conn = sqlite3.connect(DB_PATH)

# Ensure table has all needed columns
conn.execute("""
CREATE TABLE IF NOT EXISTS call_records (
    call_id           TEXT PRIMARY KEY,
    patient_phone     TEXT,
    started_at        TEXT,
    ended_at          TEXT,
    duration_secs     INTEGER DEFAULT 0,
    language          TEXT    DEFAULT 'English',
    agent_id          TEXT    DEFAULT '',
    call_status       TEXT    DEFAULT 'completed',
    patient_name      TEXT    DEFAULT '',
    patient_email     TEXT    DEFAULT '',
    booking_id        TEXT    DEFAULT '',
    appointment_date  TEXT    DEFAULT '',
    appointment_time  TEXT    DEFAULT '',
    treatment         TEXT    DEFAULT '',
    booking_status    TEXT    DEFAULT 'no_booking',
    extracted_data    TEXT    DEFAULT '{}',
    turns             TEXT    DEFAULT '[]',
    summary           TEXT    DEFAULT '',
    created_at        TEXT    DEFAULT CURRENT_TIMESTAMP,
    reminder_sent     INTEGER DEFAULT 0,
    followup_sent     INTEGER DEFAULT 0,
    bolna_raw         TEXT    DEFAULT '{}'
)
""")

# Add bolna_raw column if it doesn't exist (for existing databases)
try:
    conn.execute("ALTER TABLE call_records ADD COLUMN bolna_raw TEXT DEFAULT '{}'")
    conn.commit()
except Exception:
    pass  # Column already exists

inserted = 0
updated  = 0

for c in all_calls:
    call_id  = c.get("id", "")
    if not call_id:
        continue

    phone    = (c.get("to_number") or c.get("recipient_phone_number") or
                c.get("phone_number") or "unknown")
    status   = (c.get("call_status") or c.get("status") or "completed")
    duration = int(c.get("conversation_duration") or c.get("duration") or 0)
    started  = (c.get("created_at") or c.get("started_at") or datetime.now().isoformat())
    ended    = (c.get("ended_at") or c.get("updated_at") or started)
    agent_id = c.get("agent_id", BOLNA_AGENT_ID)

    # Parse transcript text → turns list
    transcript_raw = c.get("transcript", "") or ""
    turns = []
    for line in transcript_raw.split("\n"):
        line = line.strip()
        if line.startswith("assistant:"):
            turns.append({"role": "agent",   "content": line[10:].strip(), "timestamp": started})
        elif line.startswith("user:"):
            turns.append({"role": "patient", "content": line[5:].strip(),  "timestamp": started})

    # Extract any structured data from metadata
    meta = c.get("metadata") or c.get("extracted_data") or {}
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except Exception:
            meta = {}

    booking_status = "confirmed" if status == "completed" and len(turns) > 2 else "no_booking"

    existing = conn.execute("SELECT call_id FROM call_records WHERE call_id=?", (call_id,)).fetchone()

    if existing:
        conn.execute("""
            UPDATE call_records SET
                patient_phone=?, started_at=?, ended_at=?, duration_secs=?,
                agent_id=?, call_status=?, turns=?, extracted_data=?,
                booking_status=?, bolna_raw=?
            WHERE call_id=?
        """, (phone, started, ended, duration,
              agent_id, status, json.dumps(turns, ensure_ascii=False),
              json.dumps(meta, ensure_ascii=False),
              booking_status, json.dumps(c, ensure_ascii=False),
              call_id))
        updated += 1
    else:
        conn.execute("""
            INSERT INTO call_records
                (call_id, patient_phone, started_at, ended_at, duration_secs,
                 agent_id, call_status, turns, extracted_data, booking_status, bolna_raw)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (call_id, phone, started, ended, duration,
              agent_id, status, json.dumps(turns, ensure_ascii=False),
              json.dumps(meta, ensure_ascii=False),
              booking_status, json.dumps(c, ensure_ascii=False)))
        inserted += 1

conn.commit()
conn.close()

print(f"\nDone! Inserted: {inserted}  Updated: {updated}")

# ── Step 4: Summary ──────────────────────────────────────────────────────────
conn2 = sqlite3.connect(DB_PATH)
total_calls    = conn2.execute("SELECT count(*) FROM call_records").fetchone()[0]
total_bookings = conn2.execute(
    "SELECT count(*) FROM call_records WHERE booking_status='confirmed'"
).fetchone()[0]
conn2.close()

print(f"\n=== DATABASE SUMMARY ===")
print(f"Total call records : {total_calls}")
print(f"Confirmed bookings : {total_bookings}")
