"""
Inspect all DB records - separate real Bolna vs fake/seed data
"""
import sqlite3, json, sys
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('aria_calls.db')
conn.row_factory = sqlite3.Row

rows = conn.execute("SELECT call_id, patient_phone, call_status, booking_status, duration_secs, started_at, patient_name, language FROM call_records ORDER BY started_at").fetchall()

print(f"TOTAL RECORDS: {len(rows)}\n")

real_bolna = []
fake = []

for r in rows:
    d = dict(r)
    call_id = d['call_id']
    # Real Bolna calls have UUID format (xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)
    is_uuid = len(call_id) == 36 and call_id.count('-') == 4
    if is_uuid:
        real_bolna.append(d)
    else:
        fake.append(d)

print(f"=== FAKE/SEED RECORDS ({len(fake)}) ===")
for r in fake:
    print(f"  {r['call_id']} | phone={r['patient_phone']} | name={r['patient_name']} | status={r['booking_status']}")

print(f"\n=== REAL BOLNA RECORDS ({len(real_bolna)}) ===")
for r in real_bolna:
    print(f"  {r['call_id']} | duration={r['duration_secs']}s | status={r['call_status']} | booking={r['booking_status']} | lang={r['language']} | started={r['started_at'][:10]}")

# Also show the actual transcript of the longest call
print("\n=== SAMPLE TRANSCRIPT (longest real call) ===")
longest = max(real_bolna, key=lambda x: x['duration_secs'] or 0)
row = conn.execute("SELECT turns, bolna_raw FROM call_records WHERE call_id=?", (longest['call_id'],)).fetchone()
if row:
    raw = json.loads(row['bolna_raw'] or '{}')
    transcript = raw.get('transcript', '')
    print(f"Call: {longest['call_id']} | Duration: {longest['duration_secs']}s")
    print(f"Transcript:\n{transcript[:2000]}")

conn.close()
