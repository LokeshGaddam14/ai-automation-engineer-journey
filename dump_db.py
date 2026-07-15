import sqlite3, json

conn = sqlite3.connect('aria_calls.db')
conn.row_factory = sqlite3.Row

print("=== CALL RECORDS (12 total) ===")
rows = conn.execute("SELECT * FROM call_records ORDER BY created_at DESC LIMIT 20").fetchall()
for r in rows:
    d = dict(r)
    print(json.dumps(d, indent=2, default=str))
    print("---")

print("\n=== APPOINTMENT REMINDERS (4 total) ===")
rows2 = conn.execute("SELECT * FROM appointment_reminders").fetchall()
for r in rows2:
    print(dict(r))

conn.close()
