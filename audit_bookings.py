"""
Audit booking status: print transcript snippets to verify confirmed/no_booking accuracy
"""
import sqlite3, json, sys
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('aria_calls.db')
conn.row_factory = sqlite3.Row

rows = conn.execute("""
    SELECT call_id, call_status, booking_status, duration_secs, language, bolna_raw
    FROM call_records ORDER BY duration_secs DESC
""").fetchall()

print(f"TOTAL REAL RECORDS: {len(rows)}\n")
for r in rows:
    raw = json.loads(r['bolna_raw'] or '{}')
    transcript = raw.get('transcript', '') or ''
    cost = raw.get('total_cost', 0)
    turns_count = len([l for l in transcript.split('\n') if l.strip()])
    # Print key decision info
    print(f"ID: {r['call_id'][:8]}... | dur={r['duration_secs']}s | cost=${cost} | status={r['call_status']} | booking={r['booking_status']} | lang={r['language']} | lines={turns_count}")
    if transcript.strip():
        # Show last 2 lines of transcript
        lines = [l.strip() for l in transcript.split('\n') if l.strip()]
        for line in lines[-2:]:
            print(f"   > {line[:120]}")
    print()
conn.close()
