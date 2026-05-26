import sqlite3
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

DB_PATH = "saitama_gikai.db"
BASE_URL = "https://www.pref.saitama.lg.jp"
INDEX_URL = "https://www.pref.saitama.lg.jp/e1601/gikai-gaiyou.html"

def get_soup(url):
    res = requests.get(url, timeout=15)
    res.raise_for_status()
    res.encoding = res.apparent_encoding
    return BeautifulSoup(res.text, "html.parser")

def fetch_latest_regular_session():
    soup = get_soup(INDEX_URL)

    links = []
    for a in soup.find_all("a"):
        title = a.get_text(strip=True)
        href = a.get("href")

        if href and "定例会" in title and "令和" in title:
            links.append((title, urljoin(BASE_URL, href)))

    if links:
        return links[0]

    return None, None

def fetch_schedule_url(session_url):
    soup = get_soup(session_url)

    priority_keywords = [
        "会期日程",
        "本会議日程",
        "日程"
    ]

    links = []

    for a in soup.find_all("a"):
        title = a.get_text(strip=True)
        href = a.get("href")

        if not href:
            continue

        full_url = urljoin(BASE_URL, href)

        links.append((title, full_url))

    for keyword in priority_keywords:
        for title, full_url in links:

            if keyword in title:
                return full_url

    return session_url

def save_meeting_schedule(session_title, session_url, schedule_url):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS meeting_schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_title TEXT,
            session_url TEXT UNIQUE,
            schedule_url TEXT,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        INSERT INTO meeting_schedules
            (session_title, session_url, schedule_url)
        VALUES (?, ?, ?)
        ON CONFLICT(session_url) DO UPDATE SET
            session_title = excluded.session_title,
            schedule_url = excluded.schedule_url,
            updated_at = CURRENT_TIMESTAMP
    """, (session_title, session_url, schedule_url))

    conn.commit()
    conn.close()

def main():
    session_title, session_url = fetch_latest_regular_session()

    if not session_url:
        print("最新定例会が取得できませんでした")
        return

    schedule_url = fetch_schedule_url(session_url)

    save_meeting_schedule(session_title, session_url, schedule_url)

    print("保存完了")
    print(session_title)
    print(session_url)
    print(schedule_url)

if __name__ == "__main__":
    main()