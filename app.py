from pathlib import Path
import sqlite3

from flask import Flask, render_template, request, Response

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "saitama_gikai.db"

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static"),
)
THEME_NEWS_QUERIES = {
    "教育": "埼玉 教育 学校",
    "外国人": "埼玉 外国人政策",
    "防災": "埼玉 防災 災害",
    "子育て": "埼玉 子育て 保育",
    "医療": "埼玉 医療 病院",
}
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def search_speeches(keyword):
    if not keyword:
        return []

    conn = get_db_connection()
    cur = conn.cursor()

    words = keyword.split()
    where_clauses = []
    params = []

    for word in words:
        where_clauses.append("""
            (
                speeches.speech_text LIKE ?
                OR meetings.meeting_name LIKE ?
            )
        """)
        params.extend([
            f"%{word}%",
            f"%{word}%"
        ])

    where_sql = " AND ".join(where_clauses)

    cur.execute(f"""
        SELECT
            speeches.id,
            speeches.meeting_id,
            speeches.speech_text,
            meetings.meeting_name,
            meetings.meeting_date
        FROM speeches
        LEFT JOIN meetings
            ON speeches.meeting_id = meetings.id
        WHERE {where_sql}
        ORDER BY meetings.meeting_date DESC
        LIMIT 100
    """, params)

    rows = cur.fetchall()
    conn.close()

    results = []

    for row in rows:
        row = dict(row)

        body = row["speech_text"]
        snippet = body[:250]

        for word in words:
            pos = body.find(word)

            if pos != -1:
                start = max(pos - 80, 0)
                end = min(pos + 170, len(body))
                snippet = body[start:end]
                break

        for word in words:
            snippet = snippet.replace(
                word,
                f"<mark>{word}</mark>"
            )

        row["snippet"] = snippet
        results.append(row)

    return results


def get_latest_meetings():
    conn = get_db_connection()

    rows = conn.execute("""
        SELECT
            speeches.id,
            speeches.speech_text,
            meetings.meeting_name,
            meetings.meeting_date
        FROM speeches
        LEFT JOIN meetings
            ON speeches.meeting_id = meetings.id
        ORDER BY meetings.meeting_date DESC, speeches.id DESC
        LIMIT 3
    """).fetchall()

    conn.close()
    return rows
def get_topic_summary(keyword):
    conn = get_db_connection()

    row = conn.execute("""
        SELECT
            meetings.meeting_name,
            meetings.meeting_date,
            COUNT(*) as hit_count
        FROM speeches
        LEFT JOIN meetings
        ON speeches.meeting_id = meetings.id
        WHERE speeches.speech_text LIKE ?
        GROUP BY meetings.id
        ORDER BY meetings.meeting_date DESC
        LIMIT 1
    """, (f"%{keyword}%",)).fetchone()

    conn.close()

    if row:
        return f"{row['meeting_name']}で{row['hit_count']}件ヒット"

    return "関連議事録を検索"
def get_recent_meetings():
    conn = get_db_connection()

    rows = conn.execute("""
        SELECT
            id,
            meeting_name,
            meeting_date
        FROM meetings
        ORDER BY meeting_date DESC
        LIMIT 3
    """).fetchall()

    conn.close()
    return rows
def get_latest_schedule():
    conn = get_db_connection()

    row = conn.execute("""
        SELECT
            session_title,
            session_url,
            schedule_url,
            updated_at
        FROM meeting_schedules
        ORDER BY updated_at DESC
        LIMIT 1
    """).fetchone()

    conn.close()
    return row

@app.route("/", methods=["GET"])
def index():
    keyword = request.args.get("q", "").strip()
    results = search_speeches(keyword)

   # latest_schedule = get_latest_schedule()

    focus_words = ["外国人", "物価", "教育", "医療", "県警", "予算", "子育て", "防災"]

    
    daily_topics = [
        {
            "word": "外国人",
            "desc": get_topic_summary("外国人")
        },
        {
            "word": "教育",
            "desc": get_topic_summary("教育")
        },
        {
            "word": "予算",
            "desc": get_topic_summary("予算")
        },
    ]
    top_news_topics = [
        ("外国人", "埼玉 外国人政策"),
        ("教育", "埼玉 教育 学校"),
        ("防災", "埼玉 防災 災害"),
        ("子育て", "埼玉 子育て 保育"),
        ("医療", "埼玉 医療 病院"),
    ]

    pickup_cards = get_latest_meetings()
    recent_meetings = get_recent_meetings()

    return render_template(
    "index.html",
    keyword=keyword,
    results=results,
    count=len(results),
    focus_words=focus_words,
    daily_topics=daily_topics,
    pickup_cards=pickup_cards,
    recent_meetings=recent_meetings,
    top_news_topics=top_news_topics,
)


@app.route("/speech/<int:speech_id>")
def speech_detail(speech_id):

    keyword = request.args.get("q", "")

    news_query = THEME_NEWS_QUERIES.get(
        keyword,
        f"埼玉 {keyword}"
    )

    conn = get_db_connection()

    row = conn.execute("""
        SELECT
            speeches.id,
            speeches.speech_text,
            meetings.meeting_name,
            meetings.meeting_date
        FROM speeches
        LEFT JOIN meetings
            ON speeches.meeting_id = meetings.id
        WHERE speeches.id = ?
    """, (speech_id,)).fetchone()

    conn.close()

    if row is None:
        return "Not Found", 404

    body = row["speech_text"]

    if keyword:
        words = keyword.split()

        for word in words:
            body = body.replace(
                word,
                f"<mark>{word}</mark>"
            )

    return render_template(
        "speech.html",
        row=row,
        highlighted_body=body,
        keyword=keyword,
        news_query=news_query,
    )

@app.route("/sitemap.xml")
def sitemap():
    conn = get_db_connection()

    meetings = conn.execute("""
        SELECT id, meeting_date
        FROM meetings
        ORDER BY meeting_date DESC
    """).fetchall()

    conn.close()

    base_url = "https://あなたのドメイン"

    urls = []

    urls.append(f"""
    <url>
        <loc>{base_url}/</loc>
        <changefreq>daily</changefreq>
        <priority>1.0</priority>
    </url>
    """)

    urls.append(f"""
    <url>
        <loc>{base_url}/search</loc>
        <changefreq>daily</changefreq>
        <priority>0.8</priority>
    </url>
    """)

    for m in meetings:
        urls.append(f"""
        <url>
            <loc>{base_url}/meeting/{m['id']}</loc>
            <lastmod>{m['meeting_date']}</lastmod>
            <changefreq>monthly</changefreq>
            <priority>0.7</priority>
        </url>
        """)

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{''.join(urls)}
</urlset>
"""

    return Response(xml, mimetype="application/xml")

@app.route("/robots.txt")
def robots():
    txt = """User-agent: *
Allow: /

Sitemap: https://あなたのドメイン/sitemap.xml
"""
    return Response(txt, mimetype="text/plain")

if __name__ == "__main__":
    app.run(debug=True)