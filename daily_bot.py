import os
import json
import requests
import feedparser
from datetime import datetime, timedelta, timezone
import re

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
MAX_ITEMS = 10   # number of items per message
SEEN_FILE = "seen.json"

# --- simple summarizer: try feed summary -> first 2 sentences or trim to limit
def short_summary_from_text(text, max_chars=220, max_sentences=2):
    if not text:
        return ""
    # remove HTML tags if any
    text = re.sub('<[^<]+?>', '', text).strip()
    # normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    # try split into sentences naively
    sentences = re.split(r'(?<=[.!?])\s+', text)
    if len(sentences) >= 1:
        summary = ' '.join(sentences[:max_sentences]).strip()
    else:
        summary = text[:max_chars]
    if len(summary) > max_chars:
        # trim without breaking words
        summary = summary[:max_chars].rsplit(' ', 1)[0] + "..."
    return summary

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
                raw_summary = entry.get("summary", "") or entry.get("description", "") or ""
                text_for_match = (title + " " + raw_summary).lower()
                if not any(k.lower() in text_for_match for k in KEYWORDS):
                    continue
                if guid in seen:
                    continue
                summary_short = short_summary_from_text(raw_summary or title)
                items.append({
                    "title": title,
                    "link": link,
                    "guid": guid,
                    "summary": summary_short
                })
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
    for it in items:
        title = it.get("title", "")
        link = it.get("link", "")
        summary = it.get("summary", "")
        if summary:
            lines.append(f"• {title}\n{summary}\n{link}")
        else:
            lines.append(f"• {title}\n{link}")
    body = "\n\n".join(lines)
    msg = header + body
    if len(msg) > 3900:
        msg = msg[:3890] + "\n\n... (truncated)"
    return msg

def send_telegram(text):
    if not BOT_TOKEN or not CHAT_ID:
        ra
