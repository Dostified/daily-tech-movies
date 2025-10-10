import os
import json
import requests
import feedparser
from datetime import datetime, timedelta, timezone

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

RSS_FEEDS = [
    "https://www.theverge.com/rss/index.xml",
    "https://www.engadget.com/rss.xml",
    "https://www.gsmarena.com/rss-news-reviews.php3",
    "https://9to5google.com/feed/",
    "https://www.macrumors.com/macrumors.xml",
    "https://www.techradar.com/rss",
    "https://www.xda-developers.com/feed/",
    "https://www.imdb.com/news/movie/?ref_=nv_nw_mv",
    "https://variety.com/feed/",
    "https://www.bollywoodhungama.com/feed/"
]
KEYWORDS = ["launch", "review", "update", "leak", "AI", "movie", "trailer", "Apple", "Samsung", "Android"]
MAX_ITEMS = 12
SEEN_FILE = "seen.json"

def load_seen():
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_seen(seen):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(seen, f, ensure_ascii=False, indent=2)

def collect_items():
    items = []
    seen = set(load_seen())
    new_guids = []
    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:8]:
                title = entry.get("title", "").strip()
                link = entry.get("link", "").strip()
                guid = link or entry.get("id") or title
                text_for_match = (title + " " + entry.get("summary", "")).lower()
                if not any(k.lower() in text_for_match for k in KEYWORDS):
                    continue
                if guid in seen:
                    continue
                items.append((title, link, guid))
                new_guids.append(guid)
                if len(items) >= MAX_ITEMS:
                    break
        except Exception as e:
            print("Feed error:", feed_url, e)
        if len(items) >= MAX_ITEMS:
            break
    return items, new_guids

def build_message(items):
    IST = timezone(timedelta(hours=5, minutes=30))
    now = datetime.now(IST).strftime("%Y-%m-%d %H:%M IST")
    header = f"📰 Top Tech & Movie Updates — {now}\n\n"
    if not items:
        return header + "No new updates right now."
    lines = []
    for t, l, _ in items:
        lines.append(f"• {t}\n{l}")
    body = "\n\n".join(lines)
    msg = header + body
    if len(msg) > 3900:
        msg = msg[:3890] + "\n\n... (truncated)"
    return msg

def send_telegram(text):
    if not BOT_TOKEN or not CHAT_ID:
        raise SystemExit("Missing BOT_TOKEN or CHAT_ID")
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "disable_web_page_preview": True}
    r = requests.post(url, data=payload, timeout=30)
    r.raise_for_status()
    return r.json()

def main():
    items, new_guids = collect_items()
    msg = build_message(items)
    send_telegram(msg)
    if new_guids:
        seen = load_seen()
        seen.extend(new_guids)
        seen = seen[-500:]
        save_seen(seen)

if __name__ == "__main__":
    main()
