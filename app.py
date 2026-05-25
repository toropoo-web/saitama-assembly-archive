from pathlib import Path
import sqlite3

from flask import Flask, render_template, request

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "saitama_gikai.db"

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static"),
)


def search_speeches(keyword):
    if not keyword:
        return []

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    words = keyword.split()
    where_clauses = []
    params = []

    for word in words:
        where_clauses.append("""
            (
                speeches.body LIKE ?
                OR speeches.speaker LIKE ?
                OR meetings.meeting_name LIKE ?
            )
        """)
        params.extend([f"%{word}%", f"%{word}%", f"%{word}%"])

    where_sql = " AND ".join(where_clauses)

    cur.execute(f"""
        SELECT
            speeches.id,
            speeches.meeting_id,
            speeches.speaker,
            speeches.body,
            meetings.meeting_name,
            meetings.meeting_date

        FROM speeches

        LEFT JOIN meetings
        ON speeches.meeting_id = meetings.id

        WHERE {where_sql}

        LIMIT 100
    """, params)

    rows = cur.fetchall()

    results = []

    for row in rows:
        row = dict(row)
        body = row["body"]
        snippet = body[:250]

        for word in words:
            pos = body.find(word)
            if pos != -1:
                start = max(pos - 80, 0)
                end = min(pos + 170, len(body))
                snippet = body[start:end]
                break

        for word in words:
            snippet = snippet.replace(word, f"<mark>{word}</mark>")

        row["snippet"] = snippet
        results.append(row)

    conn.close()
    return results


@app.route("/", methods=["GET"])
def index():
    keyword = request.args.get("q", "").strip()
    results = search_speeches(keyword)

    focus_words = ["外国人", "物価", "教育", "医療", "県警", "予算", "子育て", "防災"]

    daily_topics = [
        {"word": "外国人", "desc": "令和7年12月定例会で複数発言あり"},
        {"word": "教育", "desc": "学校・人材・地域課題として出現"},
        {"word": "予算", "desc": "県政全体の議論と接続"},
    ]

    pickup_cards = []

    return render_template(
        "index.html",
        keyword=keyword,
        results=results,
        count=len(results),
        focus_words=focus_words,
        daily_topics=daily_topics,
        pickup_cards=pickup_cards,
    )


if __name__ == "__main__":
    app.run(debug=True)