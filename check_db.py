import sqlite3
import os

db_path = r'c:\Users\merve\OneDrive\Masaüstü\AkıllıToplantıAnalizi\akilli-toplanti-analizi\sesKaydı\meeting_pull_20260424_oracle\meetings_remote.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cur.fetchall()
    for table in tables:
        if 'meeting' in table[0].lower():
            cur.execute(f"SELECT * FROM {table[0]} WHERE title LIKE '%11%';")
            rows = cur.fetchall()
            for r in rows:
                print('Meeting 11 match:', r)
