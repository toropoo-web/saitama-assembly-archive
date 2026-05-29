import os
import re
import sqlite3

from topic_keywords import detect_topics

DB_PATH = "saitama_gikai.db"
TXT_DIR = "../saitama_speech_pages"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def detect_session_name(filename):
    if "2月" in filename or "02月" in filename:
        return "R8_2"

    if "12月" in filename:
        return "R7_12"

    if "6月" in filename or "06月" in filename:
        return "R8_6"

    if "9月" in filename or "09月" in filename:
        return "R8_9"

    return "unknown"


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
            source_url TEXT,
            session_name TEXT,
            official_pdf_url TEXT,
            vote_result_url TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS speeches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meeting_id INTEGER,
            speaker_name TEXT,
            speech_text TEXT,
            topic_title TEXT,
            transcript_url TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS topics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            description TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS speech_topics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            speech_id INTEGER NOT NULL,
            topic_id INTEGER NOT NULL,
            UNIQUE(speech_id, topic_id)
        )
    """)

    conn.commit()
    conn.close()


def already_imported(filename):
    conn = get_connection()
    row = conn.execute("""
        SELECT id
        FROM imported_txt_files
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


def clean_body(raw_text):
    remove_words = [
        "メインコンテンツへ移動",
        "トップへ",
        "ヘルプ",
        "発言者一覧",
        "発言単位",
        "会議録",
        "文字拡大",
        "文字縮小",
        "全選択",
        "全解除",
        "発言一覧",
        "発言者の発言を一覧表で表示します。",
        "発言一覧のすべての選択チェックボックスを選択または選択解除します。",
        "選択チェックボックス",
        "表示したい発言の選択チェックボックスを選択し、",
        "最上部の選択チェックボックスを選択することで、発言の絞り込み表示ができます。",
        "発言種別",
        "発言者列",
        "発言者プルダウン",
        "発言の絞り込み",
    ]

    body = raw_text

    for word in remove_words:
        body = body.replace(word, "")

    body = body.strip()

    if "発言者" in body:
        body = body.split("発言者", 1)[1]

    if "○招集告示" in body:
        body = "○招集告示" + body.split("○招集告示", 1)[1]

    body = body.strip()
    body = re.sub(r"会議一覧.*?日程一覧", "", body)
    body = re.sub(r"「.*?」ボタン.*?します。", "", body)
    body = re.sub(r"最上部を選択することで.*?できます。", "", body)
    body = re.sub(r"表示ができます。", "", body)
    body = re.sub(r"選択列を非表示.*?します。", "", body)
    body = re.sub(r"全ての発言を表示.*?します。", "", body)
    body = re.sub(r"対象の発言を表示.*?します。", "", body)
    body = re.sub(r"^.*?定例会", "定例会", body)

    return body.strip()


def extract_meeting_date(filename):
    date_match = re.search(r"(\d{2})月(\d{2})日", filename)

    if date_match:
        return f"{date_match.group(1)}月{date_match.group(2)}日"

    return ""


def extract_speaker_name(head):
    patterns = [
        r"[◆◎○]?\d+番（([一-龠ぁ-んァ-ンー]+?議員)）",
        r"[◆◎○]?\d+番（([一-龠ぁ-んァ-ンー]+?委員)）",
        r"○([一-龠ぁ-んァ-ンー]+?議員)",
        r"○([一-龠ぁ-んァ-ンー]+?委員)",
        r"○([一-龠ぁ-んァ-ンー]+?議長)",
        r"○([一-龠ぁ-んァ-ンー]+?副議長)",
        r"○([一-龠ぁ-んァ-ンー]+?委員長)",
        r"○([一-龠ぁ-んァ-ンー]+?副委員長)",
        r"([一-龠ぁ-んァ-ンー]+?(?:知事|副知事|教育長))",
        r"([一-龠ぁ-んァ-ンー]+?(?:部長|局長|課長|担当課長|室長|所長))",
    ]

    for pattern in patterns:
        speaker_match = re.search(pattern, head)
        if speaker_match:
            return speaker_match.group(1)

    fallback_roles = [
        "知事",
        "副知事",
        "教育長",
        "議長",
        "副議長",
        "委員長",
        "副委員長",
        "部長",
        "局長",
        "課長",
        "担当課長",
        "室長",
        "所長",
    ]

    for role in fallback_roles:
        if role in head:
            return role

    return "未分類"


def is_noise_block(block):
    noise_words = [
        "全て",
        "名簿",
        "開く",
        "閉じる",
        "発言一覧",
        "選択",
        "拍手",
        "〔拍手〕",
        "（拍手）",
        "委員会提出議案",
        "採決",
        "起立",
        "休憩",
        "再開",
        "散会",
        "開会",
        "出席議員",
        "欠席議員",
        "説明員",
        "職務のため出席した者",
    ]

    head = block[:300]

    if any(word in block[:120] for word in noise_words):
        return True

    skip_roles = [
        "○議長",
        "○副議長",
        "○委員長",
        "○副委員長",
    ]

    if any(role in head for role in skip_roles):
        return True

    return False


def import_txt_file(path, filename):
    with open(path, "r", encoding="utf-8") as f:
        raw_text = f.read()

    body = clean_body(raw_text)

    meeting_name = filename.replace(".txt", "")
    meeting_date = extract_meeting_date(filename)
    session_name = detect_session_name(filename)

    conn = get_connection()

    conn.execute("""
        INSERT INTO meetings (
            meeting_name,
            meeting_date,
            session_name,
            source_url
        )
        VALUES (?, ?, ?, ?)
    """, (
        meeting_name,
        meeting_date,
        session_name,
        ""
    ))

    meeting_id = conn.execute(
        "SELECT last_insert_rowid()"
    ).fetchone()[0]

    speech_blocks = re.split(r"(?=^[◆◎○])", body, flags=re.MULTILINE)

    for block in speech_blocks:
        block = block.strip()

        if not block:
            continue

        if is_noise_block(block):
            continue

        head = block[:300]
        speaker_name = extract_speaker_name(head)

        existing = conn.execute("""
            SELECT id
            FROM speeches
            WHERE speech_text = ?
        """, (block,)).fetchone()

        if existing:
            continue

        snippet = block[:220]

        conn.execute("""
            INSERT INTO speeches (
                meeting_id,
                speaker_name,
                speech_text,
                topic_title
            )
            VALUES (?, ?, ?, ?)
        """, (
            meeting_id,
            speaker_name,
            block,
            snippet,
        ))

        speech_id = conn.execute(
            "SELECT last_insert_rowid()"
        ).fetchone()[0]

        detected_topics = detect_topics(block)

        for slug in detected_topics:
            topic_row = conn.execute("""
                SELECT id
                FROM topics
                WHERE slug = ?
            """, (slug,)).fetchone()

            if topic_row:
                conn.execute("""
                    INSERT OR IGNORE INTO speech_topics (
                        speech_id,
                        topic_id
                    )
                    VALUES (?, ?)
                """, (
                    speech_id,
                    topic_row["id"]
                ))

    conn.commit()
    conn.close()

    mark_imported(filename)

    print("Imported:", filename, "->", session_name)


def main():
    create_tables()

    if not os.path.exists(TXT_DIR):
        print("TXTフォルダがありません:", TXT_DIR)
        return

    files = sorted([f for f in os.listdir(TXT_DIR) if f.endswith(".txt")])

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