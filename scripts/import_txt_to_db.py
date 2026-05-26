import os
import sqlite3

DB_PATH = "saitama_gikai.db"
TXT_DIR = "../saitama_speech_pages"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def create_tables():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS imported_txt_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT UNIQUE,
            imported_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS meetings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meeting_name TEXT,
            meeting_date TEXT,
            source_url TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS speeches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meeting_id INTEGER,
            speaker_name TEXT,
            speech_text TEXT
        )
    """)

    conn.commit()
    conn.close()

def already_imported(filename):
    conn = get_connection()
    row = conn.execute("""
        SELECT id FROM imported_txt_files
        WHERE filename = ?
    """, (filename,)).fetchone()
    conn.close()
    return row is not None

def mark_imported(filename):
    conn = get_connection()
    conn.execute("""
        INSERT OR IGNORE INTO imported_txt_files (filename)
        VALUES (?)
    """, (filename,))
    conn.commit()
    conn.close()

def import_txt_file(path, filename):
    with open(path, "r", encoding="utf-8") as f:
        body = f.read().strip()

    if not body:
        return

    meeting_name = filename.replace(".txt", "")

    conn = get_connection()

    conn.execute("""
        INSERT INTO meetings (
            meeting_name,
            meeting_date,
            source_url
        )
        VALUES (?, ?, ?)
    """, (
        meeting_name,
        "",
        ""
    ))

    meeting_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    conn.execute("""
        INSERT INTO speeches (
            meeting_id,
            speaker_name,
            speech_text
        )
        VALUES (?, ?, ?)
    """, (
        meeting_id,
        "未分割",
        body
    ))

    conn.commit()
    conn.close()

    mark_imported(filename)

def main():
    create_tables()

    if not os.path.exists(TXT_DIR):
        print("TXTフォルダがありません:", TXT_DIR)
        return

    files = [f for f in os.listdir(TXT_DIR) if f.endswith(".txt")]

    if not files:
        print("TXTファイルがありません")
        return

    imported_count = 0

    for filename in files:
        if already_imported(filename):
            print("SKIP:", filename)
            continue

        path = os.path.join(TXT_DIR, filename)
        import_txt_file(path, filename)

        print("IMPORTED:", filename)
        imported_count += 1

    print("完了:", imported_count, "件追加")

if __name__ == "__main__":
    main()