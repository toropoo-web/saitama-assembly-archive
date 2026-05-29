import sqlite3

DB_PATH = "saitama_gikai.db"

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

rows = conn.execute("""
    SELECT
        speeches.id,
        topics.name
    FROM speech_topics
    JOIN speeches
        ON speeches.id = speech_topics.speech_id
    JOIN topics
        ON topics.id = speech_topics.topic_id
    LIMIT 30
""").fetchall()

for row in rows:
    print(row["id"], row["name"])

conn.close()