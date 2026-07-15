import sqlite3, os

for root, dirs, files in os.walk('.'):
    dirs[:] = [d for d in dirs if d not in ['.git', 'node_modules', '__pycache__', '.venv', 'venv']]
    for f in files:
        if f.endswith('.db'):
            path = os.path.join(root, f)
            size = os.path.getsize(path)
            print(f'{path} ({size} bytes)')
            try:
                conn = sqlite3.connect(path)
                tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                print(f'  Tables: {[t[0] for t in tables]}')
                for t in tables:
                    count = conn.execute(f'SELECT count(*) FROM "{t[0]}"').fetchone()[0]
                    print(f'    {t[0]}: {count} rows')
                conn.close()
            except Exception as e:
                print(f'  Error: {e}')
