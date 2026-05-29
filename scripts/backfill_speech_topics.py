import sqlite3

DB_PATH = "saitama_gikai.db"

# キーワードでテーマに紐付け
THEME_KEYWORDS = {
    "foreigner": ["外国人", "多文化", "日本語教育", "在留"],
    "education": ["教育", "学校", "教員", "不登校", "ICT"],
    "budget": ["予算", "財政", "補助金", "事業費"],
    "disaster": ["防災", "災害", "危機管理", "避難"],
    "childcare": ["子育て", "保育", "児童福祉"],
    "welfare": ["福祉", "介護", "生活保護", "障害福祉"],
    "medical": ["医療", "病院", "保健", "地域医療"],
    "police": ["県警", "治安", "警察", "交通安全"]
}

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# speech_topics テーブルがない場合作成
cur.execute("""
CREATE TABLE IF NOT EXISTS speech_topics (
    speech_id INTEGER,
    topic_id INTEGER,
    PRIMARY KEY(speech_id, topic_id)
)
""")
conn.commit()

# topics テーブル取得
topics = cur.execute("SELECT id, slug FROM topics").fetchall()
topic_dict = {slug: tid for tid, slug in topics}

# speeches 全件取得
speeches = cur.execute("SELECT id, speech_text FROM speeches").fetchall()

inserted = 0
for speech_id, text in speeches:
    text_lower = text.lower()
    for slug, keywords in THEME_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                topic_id = topic_dict.get(slug)
                if topic_id:
                    cur.execute("""
                    INSERT OR IGNORE INTO speech_topics (speech_id, topic_id)
                    VALUES (?, ?)
                    """, (speech_id, topic_id))
                    inserted += 1
                break  # 一度ヒットしたら次のテーマへ

conn.commit()
conn.close()
print(f"Speech topics backfilled: {inserted} entries")