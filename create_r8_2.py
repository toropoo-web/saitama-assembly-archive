import sqlite3

conn = sqlite3.connect("saitama_gikai.db")
cur = conn.cursor()

cur.execute("""
INSERT INTO meetings (
    meeting_name,
    meeting_date,
    session_name
)
VALUES (
    '令和8年2月定例会',
    '2026-02-19',
    'R8_2'
)
""")

conn.commit()

cur.execute("""
SELECT id, meeting_name, session_name
FROM meetings
ORDER BY id DESC
LIMIT 3
""")

for row in cur.fetchall():
    print(row)

conn.close()