import sqlite3
import os

db_path = r'c:\Users\merve\OneDrive\Masaüstü\AkıllıToplantıAnalizi\akilli-toplanti-analizi\sesKaydı\meeting_pull_20260424_oracle\meetings_remote.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM meetings;")
    rows = cur.fetchall()
    for r in rows:
        print('Meeting:', r[0], r[1])
