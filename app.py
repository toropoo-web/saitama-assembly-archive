from flask import Flask, render_template, request
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "saitama_gikai.db"

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static")
)

def search_speeches(keyword):
    if not keyword:
        return []

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT
            speeches.id,
            speeches.speaker,
            speeches.content,
            meetings.date,
           
        FROM speeches
        JOIN meetings ON speeches.meeting_id = meetings.id
        WHERE speeches.content LIKE ?
        ORDER BY meetings.date DESC, speeches.id ASC
        LIMIT 100
    """, (f"%{keyword}%",))

    rows = cur.fetchall()
    conn.close()
    return rows

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

    pickup_cards = results[:3] if results else []

    return render_template(
        "index.html",
        keyword=keyword,
        results=results,
        count=len(results),
        focus_words=focus_words,
        daily_topics=daily_topics,
        pickup_cards=pickup_cards
    )

if __name__ == "__main__":
    app.run(debug=True)