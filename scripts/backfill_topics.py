import sqlite3

DB_PATH = "saitama_gikai.db"

TOPICS = [
    ("foreigner", "外国人", "外国人政策、多文化共生、日本語教育、治安、医療・福祉負担などに関する議事録。"),
    ("education", "教育", "学校、教員不足、不登校、教育予算、ICT教育、学校施設などに関する議事録。"),
    ("disaster", "防災", "災害対策、危機管理、避難、インフラ、FEMA、防災拠点などに関する議事録。"),
    ("budget", "予算", "県予算、財政、補助金、公共事業、財源、事業費などに関する議事録。"),
    ("childcare", "子育て", "保育、子育て支援、こども政策、保育士、児童福祉などに関する議事録。"),
    ("welfare", "福祉", "高齢者福祉、障害福祉、生活保護、介護、福祉施設などに関する議事録。"),
    ("medical", "医療", "病院、医療体制、保健医療、災害医療、地域医療などに関する議事録。"),
    ("police", "県警", "治安、交通安全、警備、取締り、県警察に関する議事録。"),
]

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

for slug, name, description in TOPICS:
    cur.execute("""
        INSERT OR REPLACE INTO topics (
            slug,
            name,
            description
        )
        VALUES (?, ?, ?)
    """, (
        slug,
        name,
        description
    ))

conn.commit()
conn.close()

print("topics backfilled")