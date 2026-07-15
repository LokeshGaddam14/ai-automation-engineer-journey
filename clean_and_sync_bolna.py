"""
CLEAN DB: Remove all fake/seed records, keep only real Bolna UUID records.
Then re-sync from Bolna with proper language detection and booking status.
"""
import os, sys, json, sqlite3, requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv(Path(__file__).parent / ".env")

BOLNA_API_KEY  = os.getenv("BOLNA_API_KEY", "")
BOLNA_AGENT_ID = os.getenv("BOLNA_AGENT_ID", "")
DB_PATH = str(Path(__file__).parent / "aria_calls.db")

conn = sqlite3.connect(DB_PATH)

# ── Step 1: Delete ALL fake/seed records (non-UUID call_ids) ─────────────────
print("Step 1: Removing fake/seed records...")
rows = conn.execute("SELECT call_id FROM call_records").fetchall()
fake_ids = []
for (call_id,) in rows:
    is_uuid = len(call_id) == 36 and call_id.count('-') == 4
    if not is_uuid:
        fake_ids.append(call_id)

if fake_ids:
    placeholders = ','.join('?' * len(fake_ids))
    conn.execute(f"DELETE FROM call_records WHERE call_id IN ({placeholders})", fake_ids)
    conn.commit()
    print(f"  Deleted {len(fake_ids)} fake records: {fake_ids}")
else:
    print("  No fake records found.")

# ── Step 2: Fetch fresh data from Bolna API ──────────────────────────────────
print("\nStep 2: Fetching real calls from Bolna API...")
headers_bolna = {"Authorization": f"Bearer {BOLNA_API_KEY}"}

resp = requests.get(
    f"https://api.bolna.dev/v1/agent/{BOLNA_AGENT_ID}/executions",
    headers=headers_bolna,
    params={"page_number": 1, "page_size": 100},
    timeout=20,
)
resp.raise_for_status()
executions = resp.json()
if not isinstance(executions, list):
    executions = executions.get("data", [])

print(f"  Fetched {len(executions)} real executions from Bolna.")

# ── Step 3: Detect language from transcript ──────────────────────────────────
def detect_language(transcript: str) -> str:
    if not transcript:
        return "English"
    # Telugu Unicode block: 0C00–0C7F
    telugu_chars = sum(1 for c in transcript if '\u0C00' <= c <= '\u0C7F')
    # Hindi/Devanagari: 0900–097F
    hindi_chars = sum(1 for c in transcript if '\u0900' <= c <= '\u097F')
    # Tamil: 0B80–0BFF
    tamil_chars = sum(1 for c in transcript if '\u0B80' <= c <= '\u0BFF')
    total = len(transcript)
    if total == 0:
        return "English"
    if telugu_chars / total > 0.05:
        return "Telugu"
    if hindi_chars / total > 0.05:
        return "Hindi"
    if tamil_chars / total > 0.05:
        return "Tamil"
    return "English"

# ── Step 4: Detect booking from transcript ───────────────────────────────────
def detect_booking(transcript: str, status: str, duration: float) -> str:
    if status == 'busy' or not transcript:
        return "no_booking"
    if duration and duration < 5:
        return "no_booking"
    t_lower = transcript.lower()
    # Booking keywords in English, Telugu, Hindi
    booked_keywords = [
        "appointment",  "booked", "confirmed", "scheduled", "book",
        "అపాయింట్మెంట్", "బుక్", "నిర్ధారించబడింది",
        "अपॉइंटमेंट", "बुक",
    ]
    if any(kw in transcript for kw in booked_keywords):
        return "confirmed"
    return "no_booking"

# ── Step 5: Parse transcript into turns ──────────────────────────────────────
def parse_turns(transcript: str, started: str) -> list:
    turns = []
    for line in transcript.split("\n"):
        line = line.strip()
        if line.startswith("assistant:"):
            turns.append({"role": "agent",   "content": line[10:].strip(), "timestamp": started})
        elif line.startswith("user:"):
            turns.append({"role": "patient", "content": line[5:].strip(),  "timestamp": started})
    return turns

# ── Step 6: Add bolna_raw column if needed ──────────────────────────────────
try:
    conn.execute("ALTER TABLE call_records ADD COLUMN bolna_raw TEXT DEFAULT '{}'")
    conn.commit()
except Exception:
    pass

# ── Step 7: Upsert all real Bolna calls ─────────────────────────────────────
print("\nStep 3: Syncing real Bolna calls to database...")
inserted = 0
updated  = 0

for c in executions:
    call_id = c.get("id", "")
    if not call_id:
        continue

    phone     = c.get("to_number") or c.get("recipient_phone_number") or "N/A"
    status    = c.get("call_status") or c.get("status") or "completed"
    duration  = float(c.get("conversation_duration") or 0)
    started   = c.get("created_at") or c.get("started_at") or datetime.utcnow().isoformat()
    ended     = c.get("ended_at") or c.get("updated_at") or started
    agent_id  = c.get("agent_id", BOLNA_AGENT_ID)
    cost      = c.get("total_cost") or 0.0

    transcript_raw = c.get("transcript", "") or ""
    language       = detect_language(transcript_raw)
    booking_status = detect_booking(transcript_raw, status, duration)
    turns          = parse_turns(transcript_raw, started)

    existing = conn.execute("SELECT call_id FROM call_records WHERE call_id=?", (call_id,)).fetchone()

    row_data = (
        phone, started, ended, int(duration),
        language, agent_id, status,
        "", "", "", "", "", "",
        booking_status,
        json.dumps({"cost": cost, "language": language, "booking_status": booking_status}, ensure_ascii=False),
        json.dumps(turns, ensure_ascii=False),
        "",  # summary
        json.dumps(c, ensure_ascii=False),
    )

    if existing:
        conn.execute("""
            UPDATE call_records SET
                patient_phone=?, started_at=?, ended_at=?, duration_secs=?,
                language=?, agent_id=?, call_status=?,
                patient_name=?, patient_email=?, booking_id=?,
                appointment_date=?, appointment_time=?, treatment=?,
                booking_status=?, extracted_data=?, turns=?, summary=?, bolna_raw=?
            WHERE call_id=?
        """, (*row_data, call_id))
        updated += 1
    else:
        conn.execute("""
            INSERT INTO call_records
                (call_id, patient_phone, started_at, ended_at, duration_secs,
                 language, agent_id, call_status,
                 patient_name, patient_email, booking_id,
                 appointment_date, appointment_time, treatment,
                 booking_status, extracted_data, turns, summary, bolna_raw)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (call_id, *row_data))
        inserted += 1

conn.commit()

# ── Step 8: Final summary ────────────────────────────────────────────────────
total_calls     = conn.execute("SELECT count(*) FROM call_records").fetchone()[0]
total_bookings  = conn.execute("SELECT count(*) FROM call_records WHERE booking_status='confirmed'").fetchone()[0]
total_completed = conn.execute("SELECT count(*) FROM call_records WHERE call_status='completed'").fetchone()[0]
lang_counts     = conn.execute("SELECT language, count(*) FROM call_records GROUP BY language").fetchall()
total_duration  = conn.execute("SELECT sum(duration_secs) FROM call_records").fetchone()[0] or 0
conn.close()

print(f"\n{'='*50}")
print(f"DATABASE CLEANED & SYNCED — REAL DATA ONLY")
print(f"{'='*50}")
print(f"  Fake records deleted : {len(fake_ids)}")
print(f"  Inserted             : {inserted}")
print(f"  Updated              : {updated}")
print(f"  Total calls          : {total_calls}")
print(f"  Completed calls      : {total_completed}")
print(f"  Confirmed bookings   : {total_bookings}")
print(f"  Total talk time      : {total_duration}s ({round(total_duration/60, 1)} min)")
print(f"  Languages            : {dict(lang_counts)}")
print(f"{'='*50}")
print("\nDone! Database now contains ONLY real Bolna AI call data.")
