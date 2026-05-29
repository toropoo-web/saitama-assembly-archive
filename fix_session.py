import sqlite3

conn = sqlite3.connect("saitama_gikai.db")
cur = conn.cursor()

cur.execute("""
UPDATE meetings
SET session_name='R7_12'
WHERE session_name='R8_2'
""")

conn.commit()

cur.execute("""
SELECT id, meeting_name, session_name
FROM meetings
""")

for row in cur.fetchall():
    print(row)

conn.close()