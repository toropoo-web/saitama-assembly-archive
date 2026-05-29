import sqlite3
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

DB_PATH = "saitama_gikai.db"
BASE_URL = "https://www.pref.saitama.lg.jp/e1601/gikai-gaiyou/r0802/4.html"
MEETING_ID = 9

def clean(text):
    return " ".join(text.split())

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("DELETE FROM speeches WHERE meeting_id = ?", (MEETING_ID,))
    conn.commit()
    print("既存R8_2削除完了")
    html = requests.get(BASE_URL, timeout=20)
    html.encoding = html.apparent_encoding
    soup = BeautifulSoup(html.text, "html.parser")

    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/r0802/4/" in href and href.endswith(".html"):
            url = urljoin(BASE_URL, href)
            title = clean(a.get_text())
            links.append((title, url))

    # 重複除去
    seen = set()
    unique_links = []
    for title, url in links:
        if url not in seen:
            seen.add(url)
            unique_links.append((title, url))

    print("取得対象:", len(unique_links), "件")

    for topic_title, url in unique_links:
        page = requests.get(url, timeout=20)
        page.encoding = page.apparent_encoding
        psoup = BeautifulSoup(page.text, "html.parser")

        h1 = psoup.find("h1")
        h1_text = clean(h1.get_text()) if h1 else ""

        speaker_name = ""
        if "（" in h1_text:
            speaker_name = h1_text.split("（")[-1].replace("）", "")
        else:
            speaker_name = h1_text

        body_text = psoup.get_text("\n")

        start = body_text.find("Q　")
        if start == -1:
            start = body_text.find("Q ")

        if start != -1:
            main_text = clean(body_text[start:])
        else:
            main_text = clean(body_text)

        cur.execute("""
            INSERT INTO speeches (
                meeting_id,
                speaker_name,
                speech_text,
                topic_title,
                transcript_url
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            MEETING_ID,
            speaker_name,
            main_text,
            topic_title,
            url
        ))

        print("INSERT:", speaker_name, topic_title)
        time.sleep(0.5)

    conn.commit()
    conn.close()

    print("完了")

if __name__ == "__main__":
    main()