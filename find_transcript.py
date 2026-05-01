import sqlite3
import os
import json

db_path = r'c:\Users\merve\OneDrive\Masaüstü\AkıllıToplantıAnalizi\akilli-toplanti-analizi\sesKaydı\meeting_pull_20260424_oracle\meetings_remote.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cur.fetchall()
    
    for table in tables:
        if 'transcript' in table[0].lower() or 'meeting' in table[0].lower() or 'session' in table[0].lower():
            try:
                cur.execute(f"SELECT * FROM {table[0]}")
                rows = cur.fetchall()
                for r in rows:
                    row_str = str(r)
                    if 'Merve' in row_str and 'Ilgın' in row_str and 'retention' in row_str:
                        print(f"FOUND MATCH IN TABLE {table[0]}:")
                        print(r)
            except Exception as e:
                pass
