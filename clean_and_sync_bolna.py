"""
CLEAN DB: Remove all fake/seed records, keep only real Bolna UUID records.
Then re-sync from Bolna with proper language detection, booking status, and
extracted_data mapping (patient name, date, time, etc)
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

print("Step 1: Removing fake/seed records...")
rows = conn.execute("SELECT call_id FROM call_records").fetchall()
fake_ids = [r[0] for r in rows if len(r[0]) != 36 or r[0].count('-') != 4]
if fake_ids:
    placeholders = ','.join('?' * len(fake_ids))
    conn.execute(f"DELETE FROM call_records WHERE call_id IN ({placeholders})", fake_ids)
    conn.commit()
    print(f"  Deleted {len(fake_ids)} fake records.")

print("\nStep 2: Fetching real calls from Bolna API...")
headers_bolna = {"Authorization": f"Bearer {BOLNA_API_KEY}"}

resp = requests.get(
    f"https://api.bolna.dev/v1/agent/{BOLNA_AGENT_ID}/executions",
    headers=headers_bolna,
    params={"page_number": 1, "page_size": 100},
    timeout=20,
)
resp.raise_for_status()
executions = resp.json().get("data", []) if isinstance(resp.json(), dict) else resp.json()

print(f"  Fetched {len(executions)} real executions from Bolna.")

def detect_language(transcript: str) -> str:
    if not transcript: return "English"
    telugu_chars = sum(1 for c in transcript if '\u0C00' <= c <= '\u0C7F')
    hindi_chars = sum(1 for c in transcript if '\u0900' <= c <= '\u097F')
    total = len(transcript)
    if total == 0: return "English"
    if telugu_chars / total > 0.05: return "Telugu"
    if hindi_chars / total > 0.05: return "Hindi"
    return "English"

def detect_booking_accurate(transcript: str, status: str, duration: float, cost: float) -> str:
    if status == 'busy' or not transcript: return "no_booking"
    lines = [l.strip() for l in transcript.split('\n') if l.strip()]
    user_lines   = [l for l in lines if l.startswith('user:')]
    agent_lines  = [l for l in lines if l.startswith('assistant:')]
    if not user_lines: return "no_booking"
    full_agent_text = ' '.join(agent_lines).lower()
    
    confirmed_phrases = [
        "కన్ఫర్మ్ అయింది", "బుక్ చేసుకున్నాను", "అపాయింట్‌మెంట్ బుక్", 
        "అపాయింట్మెంట్ కోసం ధన్యవాదాలు", "నిర్ధారించబడింది",
        "appointment confirmed", "appointment booked", "successfully booked",
    ]
    if any(p in full_agent_text for p in confirmed_phrases): return "confirmed"
    if duration >= 60 and cost > 5.0 and len(user_lines) >= 3: return "confirmed"
    return "no_booking"

# Extract deeply nested Bolna extracted_data values
def get_extracted_val(ex_data: dict, key: str) -> str:
    if not ex_data: return ""
    v = ex_data.get(key)
    if isinstance(v, dict):
        # some structure is {"patient_name": {"patient_name": {"subjective": "Lokesh"}}}
        inner = v.get(key, v)
        if isinstance(inner, dict):
            return inner.get("subjective", "")
    return ""

print("\nStep 3: Syncing real Bolna calls to database...")
inserted, updated = 0, 0

for c in executions:
    call_id = c.get("id", "")
    if not call_id: continue

    phone     = c.get("to_number") or c.get("recipient_phone_number") or "N/A"
    status    = c.get("call_status") or c.get("status") or "completed"
    duration  = float(c.get("conversation_duration") or 0)
    started   = c.get("created_at") or c.get("started_at") or datetime.utcnow().isoformat()
    ended     = c.get("ended_at") or c.get("updated_at") or started
    agent_id  = c.get("agent_id", BOLNA_AGENT_ID)
    cost      = c.get("total_cost") or 0.0

    transcript_raw = c.get("transcript", "") or ""
    language       = detect_language(transcript_raw)
    booking_status = detect_booking_accurate(transcript_raw, status, duration, cost)
    
    turns = []
    for line in transcript_raw.split("\n"):
        line = line.strip()
        if line.startswith("assistant:"):
            turns.append({"role": "agent", "content": line[10:].strip(), "timestamp": started})
        elif line.startswith("user:"):
            turns.append({"role": "patient", "content": line[5:].strip(), "timestamp": started})

    # Extract real data!
    ex = c.get("extracted_data") or {}
    patient_name = get_extracted_val(ex, "patient_name")
    patient_email = get_extracted_val(ex, "email")
    appt_date = get_extracted_val(ex, "appointment_date")
    appt_time = get_extracted_val(ex, "appointment_time")
    treatment = get_extracted_val(ex, "treatment")
    if "did not specify" in treatment.lower() or "unknown" in treatment.lower():
        treatment = ""
        
    summary = get_extracted_val(ex, "General") or ""

    extracted_data_json = {
        "cost": cost, 
        "language": language, 
        "booking_status": booking_status,
        "patientName": patient_name,
        "appointmentDate": appt_date,
        "appointmentTime": appt_time,
        "treatment": treatment,
        "email": patient_email,
        "summary": summary
    }

    existing = conn.execute("SELECT call_id FROM call_records WHERE call_id=?", (call_id,)).fetchone()

    row_data = (
        phone, started, ended, int(duration), language, agent_id, status,
        patient_name, patient_email, "", appt_date, appt_time, treatment, booking_status,
        json.dumps(extracted_data_json, ensure_ascii=False),
        json.dumps(turns, ensure_ascii=False),
        summary,
        json.dumps(c, ensure_ascii=False),
    )

    if existing:
        conn.execute("""
            UPDATE call_records SET
                patient_phone=?, started_at=?, ended_at=?, duration_secs=?, language=?, agent_id=?, call_status=?,
                patient_name=?, patient_email=?, booking_id=?, appointment_date=?, appointment_time=?, treatment=?, booking_status=?,
                extracted_data=?, turns=?, summary=?, bolna_raw=?
            WHERE call_id=?
        """, (*row_data, call_id))
        updated += 1
    else:
        conn.execute("""
            INSERT INTO call_records
                (call_id, patient_phone, started_at, ended_at, duration_secs, language, agent_id, call_status,
                 patient_name, patient_email, booking_id, appointment_date, appointment_time, treatment, booking_status,
                 extracted_data, turns, summary, bolna_raw)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (call_id, *row_data))
        inserted += 1

conn.commit()
conn.close()

print(f"\n✅ Synced successfully. {updated} updated, {inserted} inserted.")
