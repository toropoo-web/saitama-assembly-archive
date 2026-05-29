from pathlib import Path
import sqlite3
import feedparser

from flask import (
    Flask,
    render_template,
    request,
    Response,
)

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
    "予算": "埼玉 予算 県議会",
    "福祉": "埼玉 福祉 介護",
}

TOPICS = [
    {"name": "外国人", "slug": "foreigner"},
    {"name": "教育", "slug": "education"},
    {"name": "防災", "slug": "disaster"},
    {"name": "予算", "slug": "budget"},
    {"name": "子育て", "slug": "childcare"},
    {"name": "福祉", "slug": "welfare"},
    {"name": "医療", "slug": "medical"},
]


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def highlight_words(text, words):
    if not text:
        return ""

    for word in words:
        if word:
            text = text.replace(
                word,
                f"<mark>{word}</mark>"
            )

    return text


def make_snippet(
    text,
    words=None,
    default_len=260,
):
    if not text:
        return ""

    words = words or []

    for word in words:
        pos = text.find(word)

        if pos != -1:
            start = max(pos - 80, 0)
            end = min(pos + 180, len(text))

            snippet = text[start:end]

            return highlight_words(
                snippet,
                words
            )

    return highlight_words(
        text[:default_len],
        words
    )


def get_topic_count(keyword):
    conn = get_db_connection()

    row = conn.execute("""
        SELECT COUNT(*)
        FROM speeches
        WHERE speech_text LIKE ?
    """, (f"%{keyword}%",)).fetchone()

    conn.close()

    return row[0]


def get_topic_speaker(keyword):
    conn = get_db_connection()

    row = conn.execute("""
        SELECT speaker_name
        FROM speeches
        WHERE speech_text LIKE ?
        AND speaker_name IS NOT NULL
        AND speaker_name != ''
        ORDER BY id DESC
        LIMIT 1
    """, (f"%{keyword}%",)).fetchone()

    conn.close()

    if row:
        return row["speaker_name"]

    return "確認中"


def get_topic_summary(keyword):
    conn = get_db_connection()

    row = conn.execute("""
        SELECT
            meetings.meeting_name,
            meetings.meeting_date,
            COUNT(*) AS hit_count
        FROM speeches
        LEFT JOIN meetings
            ON speeches.meeting_id = meetings.id
        WHERE speeches.speech_text LIKE ?
        GROUP BY meetings.id
        ORDER BY meetings.id DESC
        LIMIT 1
    """, (f"%{keyword}%",)).fetchone()

    conn.close()

    if row:
        return (
            f"{row['meeting_name']}で"
            f"{row['hit_count']}件ヒット"
        )

    return "関連議事録を検索"

def get_featured_speaker():

    conn = get_db_connection()

    row = conn.execute("""
        SELECT
            speaker_name
        FROM speeches
        WHERE speaker_name != '未分類'
        GROUP BY speaker_name
        ORDER BY COUNT(*) DESC
        LIMIT 1
    """).fetchone()

    conn.close()

    return row["speaker_name"]    

def get_speaker_topic_cards(speaker_name):
    conn = get_db_connection()

    themes = [
        "外国人",
        "教育",
        "予算",
        "防災",
    ]

    cards = []

    for theme in themes:

        row = conn.execute("""
            SELECT
                id,
                speech_text
            FROM speeches
            WHERE speaker_name = ?
            AND speech_text LIKE ?
            ORDER BY id DESC
            LIMIT 1
        """, (
            speaker_name,
            f"%{theme}%"
        )).fetchone()

        if row:

            cards.append({
                "theme": theme,
                "snippet": row["speech_text"][:70],
                "link": f"/?q={speaker_name} {theme}#results"
            })

    conn.close()

    return cards

def search_speeches(keyword):
    if not keyword:
        return []

    words = keyword.split()

    where_clauses = []
    params = []

    for word in words:

        where_clauses.append("""
            (
                speeches.speech_text LIKE ?
                OR speeches.speaker_name LIKE ?
                OR meetings.meeting_name LIKE ?
            )
        """)

        params.extend([
            f"%{word}%",
            f"%{word}%",
            f"%{word}%",
        ])

    where_sql = " AND ".join(where_clauses)

    conn = get_db_connection()

    rows = conn.execute(f"""
        SELECT
            speeches.id,
            speeches.meeting_id,
            speeches.speaker_name,
            speeches.topic_title,
            speeches.speech_text,
            meetings.meeting_name,
            meetings.meeting_date,
            meetings.session_name
        FROM speeches
        LEFT JOIN meetings
            ON speeches.meeting_id = meetings.id
        WHERE {where_sql}
        ORDER BY speeches.id DESC
        LIMIT 100
        """, params).fetchall()

    print(where_sql)
    print(params)

    conn.close()

    results = []

    for row in rows:

        row = dict(row)

        row["snippet"] = make_snippet(
            row["speech_text"],
            words
        )

        results.append(row)

    return results

def get_speakers():

    conn = get_db_connection()

    rows = conn.execute("""
        SELECT
            speaker_name,
            COUNT(*) AS cnt
        FROM speeches
        WHERE speaker_name IS NOT NULL
        AND speaker_name != ''
        AND speaker_name != '未分類'
        GROUP BY speaker_name
        ORDER BY cnt DESC
    """).fetchall()

    conn.close()

    return rows

def get_latest_meetings():
    conn = get_db_connection()

    rows = conn.execute("""
        SELECT
            speeches.id,
            speeches.speaker_name,
            speeches.speech_text,
            meetings.meeting_name,
            meetings.meeting_date
        FROM speeches
        LEFT JOIN meetings
            ON speeches.meeting_id = meetings.id
        WHERE meetings.session_name = 'R8_2'
        ORDER BY speeches.id DESC
        LIMIT 3
    """).fetchall()

    conn.close()

    return rows

def get_rss_news(feed_url, limit=3):
    feed = feedparser.parse(feed_url)

    news_items = []

    for entry in feed.entries[:limit]:

        news_items.append({
            "title": entry.get("title", ""),
            "url": entry.get("link", "#"),
        })

    return news_items

@app.route("/")
def index():

    keyword = request.args.get(
        "q",
        ""
    ).strip()

    results = search_speeches(keyword)
        
    yahoo_news = get_rss_news(
        "https://news.yahoo.co.jp/rss/topics/domestic.xml"
    )

    saitama_news = get_rss_news(
            "https://news.google.com/rss/search?q=埼玉&hl=ja&gl=JP&ceid=JP:ja"
        )

    daily_topics = [
    {
        "word": "外国人",
        "slug": "foreigner",
        "desc": get_topic_summary("外国人"),
        "count": get_topic_count("外国人"),
        "speaker": get_topic_speaker("外国人"),
    },
    {
        "word": "教育",
        "slug": "education",
        "desc": get_topic_summary("教育"),
        "count": get_topic_count("教育"),
        "speaker": get_topic_speaker("教育"),
    },
    {
        "word": "予算",
        "slug": "budget",
        "desc": get_topic_summary("予算"),
        "count": get_topic_count("予算"),
        "speaker": get_topic_speaker("予算"),
    },

    ]

    hot_topics = [
        {
            "name": topic["name"],
            "slug": topic["slug"],
            "count": get_topic_count(
                topic["name"]
            ),
            "speaker": get_topic_speaker(
                topic["name"]
            ),
        }
        for topic in TOPICS
    ]

    top_news_topics = [
        ("外国人", "埼玉 外国人政策"),
        ("教育", "埼玉 教育 学校"),
        ("防災", "埼玉 防災 災害"),
        ("子育て", "埼玉 子育て 保育"),
        ("医療", "埼玉 医療 病院"),
    ]

    pickup_cards = get_latest_meetings()

    selected_speaker = request.args.get(
    "speaker",
    get_featured_speaker()
    )

    speaker_topic_cards = get_speaker_topic_cards(
        selected_speaker
    )

    speakers = get_speakers()

    return render_template(
        "index.html",
        keyword=keyword,
        results=results,
        count=len(results),
        daily_topics=daily_topics,
        pickup_cards=pickup_cards,
        top_news_topics=top_news_topics,
        hot_topics=hot_topics,

        yahoo_news=yahoo_news,
        saitama_news=saitama_news,

        featured_speaker=selected_speaker,
        speaker_topic_cards=speaker_topic_cards,
        speakers=speakers,
    )


@app.route("/speech/<int:speech_id>")
def speech_detail(speech_id):

    keyword = request.args.get(
        "q",
        ""
    ).strip()

    news_query = THEME_NEWS_QUERIES.get(
        keyword,
        f"埼玉 {keyword}" if keyword else "埼玉 県議会"
    )

    conn = get_db_connection()

    row = conn.execute("""
        SELECT
            speeches.id,
            speeches.speaker_name,
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

    words = keyword.split() if keyword else []

    highlighted_body = highlight_words(
        row["speech_text"],
        words
    )

    return render_template(
        "speech.html",
        row=row,
        highlighted_body=highlighted_body,
        keyword=keyword,
        news_query=news_query,
    )


@app.route("/topics")
def topics_index():

    conn = get_db_connection()

    topics = conn.execute("""
        SELECT
            topics.id,
            topics.slug,
            topics.name,
            topics.description,
            COUNT(speech_topics.speech_id)
                AS speech_count,
            MAX(meetings.meeting_date)
                AS latest_date
        FROM topics
        LEFT JOIN speech_topics
            ON topics.id = speech_topics.topic_id
        LEFT JOIN speeches
            ON speech_topics.speech_id = speeches.id
        LEFT JOIN meetings
            ON speeches.meeting_id = meetings.id
        GROUP BY topics.id
        ORDER BY speech_count DESC
    """).fetchall()

    conn.close()

    return render_template(
        "topics.html",
        topics=topics,
    )


@app.route("/topics/<slug>")
def topic_detail(slug):

    conn = get_db_connection()

    topic = conn.execute("""
        SELECT *
        FROM topics
        WHERE slug = ?
    """, (slug,)).fetchone()

    if topic is None:
        conn.close()

        return "Topic not found", 404

    speeches = conn.execute("""
        SELECT
            speeches.id,
            speeches.speaker_name,
            speeches.speech_text,
            meetings.meeting_name,
            meetings.meeting_date
        FROM speeches
        JOIN speech_topics
            ON speeches.id = speech_topics.speech_id
        JOIN topics
            ON speech_topics.topic_id = topics.id
        LEFT JOIN meetings
            ON speeches.meeting_id = meetings.id
        WHERE topics.slug = ?
        ORDER BY speeches.id DESC
        LIMIT 20
    """, (slug,)).fetchall()

    conn.close()

    results = []

    for speech in speeches:

        speech = dict(speech)

        speech["snippet"] = make_snippet(
            speech["speech_text"],
            [topic["name"]],
            default_len=300,
        )

        results.append(speech)

    return render_template(
        "topic_detail.html",
        topic=topic,
        speeches=results,
    )


@app.route("/r8/<slug>")
def r8_topic(slug):
    return topic_detail(slug)


@app.route("/session/<session_name>")
def session_hub(session_name):

    conn = get_db_connection()

    rows = conn.execute("""
        SELECT
            meetings.id AS meeting_id,
            meetings.meeting_name,
            meetings.meeting_date,
            meetings.session_name,
            speeches.id AS speech_id,
            speeches.speaker_name,
            speeches.topic_title,
            substr(
                speeches.speech_text,
                1,
                180
            ) AS snippet
        FROM speeches
        JOIN meetings
            ON speeches.meeting_id = meetings.id
        WHERE meetings.session_name = ?
        ORDER BY speeches.speaker_name ASC, speeches.id ASC
    """, (session_name,)).fetchall()

    conn.close()

    speakers = {}

    for row in rows:
        name = row["speaker_name"]

        if name not in speakers:
            speakers[name] = []

        speakers[name].append(row)

    return render_template(
        "session_hub.html",
        session_name=session_name,
        speakers=speakers,
    )


@app.route("/sitemap.xml")
def sitemap():

    conn = get_db_connection()

    speeches = conn.execute("""
        SELECT
            speeches.id
        FROM speeches
        ORDER BY id DESC
        LIMIT 5000
    """).fetchall()

    topics = conn.execute("""
        SELECT slug
        FROM topics
        ORDER BY id ASC
    """).fetchall()

    conn.close()

    base_url = "https://saitama-assembly-archive.onrender.com"

    urls = []

    urls.append(f"""
    <url>
        <loc>{base_url}/</loc>
    </url>
    """)

    urls.append(f"""
    <url>
        <loc>{base_url}/topics</loc>
    </url>
    """)

    for topic in topics:

        urls.append(f"""
        <url>
            <loc>
                {base_url}/topics/{topic['slug']}
            </loc>
        </url>
        """)

    for speech in speeches:

        urls.append(f"""
        <url>
            <loc>
                {base_url}/speech/{speech['id']}
            </loc>
        </url>
        """)

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset
xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">

{''.join(urls)}

</urlset>
"""

    return Response(
        xml,
        mimetype="application/xml"
    )


@app.route("/robots.txt")
def robots():

    txt = """User-agent: *
Allow: /

Sitemap: https://saitama-assembly-archive.onrender.com/sitemap.xml
"""

    return Response(
        txt,
        mimetype="text/plain"
    )


if __name__ == "__main__":
    app.run(debug=True)