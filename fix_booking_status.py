"""
Fix booking status with accurate logic:
- Only real bookings where user actually spoke AND agent confirmed
- Intro-only calls (no user turn) = no_booking
"""
import sqlite3, json, sys
sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = 'aria_calls.db'
conn = sqlite3.connect(DB_PATH)

def detect_booking_accurate(transcript: str, status: str, duration: float, cost: float) -> str:
    """
    Accurate booking detection:
    - Must have at least one user turn
    - Agent must have said a confirmation phrase
    - Cost $0.0 with only intro = no_booking
    """
    if status == 'busy' or not transcript:
        return "no_booking"

    lines = [l.strip() for l in transcript.split('\n') if l.strip()]
    user_lines   = [l for l in lines if l.startswith('user:')]
    agent_lines  = [l for l in lines if l.startswith('assistant:')]

    # No user spoke at all = no booking
    if not user_lines:
        return "no_booking"

    # Agent must have explicitly confirmed
    full_agent_text = ' '.join(agent_lines).lower()
    
    # Telugu confirmation phrases
    telugu_confirmed = [
        "కన్ఫర్మ్ అయింది",  # appointment confirmed
        "బుక్ చేసుకున్నాను",  # I have booked
        "అపాయింట్‌మెంట్ బుక్",  # appointment book
        "అపాయింట్మెంట్ కోసం ధన్యవాదాలు",  # thanks for appointment
    ]
    english_confirmed = [
        "appointment confirmed",
        "appointment booked",
        "i've booked",
        "i have booked",
        "successfully booked",
        "slot is confirmed",
    ]
    
    for phrase in telugu_confirmed + english_confirmed:
        if phrase in full_agent_text:
            return "confirmed"
    
    # Also check if booking was in progress but call had meaningful conversation
    if duration >= 60 and cost > 5.0 and len(user_lines) >= 3:
        # Long call with multiple user turns - likely a booking
        return "confirmed"
    
    return "no_booking"

# Update all records
rows = conn.execute("SELECT call_id, call_status, duration_secs, bolna_raw FROM call_records").fetchall()
updates = []
for call_id, status, duration, bolna_raw in rows:
    raw = json.loads(bolna_raw or '{}')
    transcript = raw.get('transcript', '') or ''
    cost = float(raw.get('total_cost') or 0)
    new_booking = detect_booking_accurate(transcript, status, duration or 0, cost)
    updates.append((new_booking, call_id))

conn.executemany("UPDATE call_records SET booking_status=? WHERE call_id=?", updates)
conn.commit()

# Final accurate stats
total       = conn.execute("SELECT count(*) FROM call_records").fetchone()[0]
completed   = conn.execute("SELECT count(*) FROM call_records WHERE call_status='completed'").fetchone()[0]
confirmed   = conn.execute("SELECT count(*) FROM call_records WHERE booking_status='confirmed'").fetchone()[0]
no_booking  = conn.execute("SELECT count(*) FROM call_records WHERE booking_status='no_booking'").fetchone()[0]
langs       = conn.execute("SELECT language, count(*) FROM call_records GROUP BY language").fetchall()
total_dur   = conn.execute("SELECT sum(duration_secs) FROM call_records").fetchone()[0] or 0
total_cost_rows = conn.execute("SELECT bolna_raw FROM call_records").fetchall()
total_cost  = sum(float(json.loads(r[0] or '{}').get('total_cost', 0)) for r in total_cost_rows)

conn.close()

print("=" * 55)
print("FINAL REAL DATABASE STATS (Bolna AI data only)")
print("=" * 55)
print(f"  Total calls          : {total}")
print(f"  Completed calls      : {completed}")
print(f"  Busy/missed          : {total - completed}")
print(f"  Confirmed bookings   : {confirmed}")
print(f"  No booking / dropped : {no_booking}")
print(f"  Booking rate         : {round(confirmed/total*100, 1)}%")
print(f"  Total talk time      : {total_dur}s ({round(total_dur/60, 1)} min)")
print(f"  Total AI cost        : ${round(total_cost, 2)}")
print(f"  Languages            : {dict(langs)}")
print("=" * 55)
