# daily_bot.py
# Sends summarized tech/gadget/movie updates to Telegram.
# Requirements: requests, feedparser, beautifulsoup4

import os
import json
import requests
import feedparser
from datetime import datetime, timedelta, timezone
import re
from bs4 import BeautifulSoup

# --- Config (set secrets in GitHub, not here) ---
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

KEYWORDS = [
    "launch", "review", "update", "leak", "AI",
    "movie", "trailer", "Apple", "Samsung", "Android"
]

MAX_ITEMS = 6
SEEN_FILE = "seen.json"
REQUEST_TIMEOUT = 8
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100 Safari/537.36"

# --- Helper functions ---

def short_summary_from_text(text, max_chars=220, max_sentences=2):
    if not text:
        return ""
    text = re.sub("<[^<]+?>", "", text).strip()
    text = re.sub(r"\s+", " ", text)
    sentences = re.split(r"(?<=[.!?])\s+", text)
    summary = " ".join(sentences[:max_sentences]).strip()
    if len(summary) > max_chars:
        summary = summary[:max_chars].rsplit(" ", 1)[0] + "..."
    return summary


def fetch_page_summary(url):
    """Try to fetch short meta or paragraph summary from the article."""
    if not url:
        return ""
    try:
        headers = {"User-Agent": USER_AGENT}
        r = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        # Try meta description
        meta = (soup.find("meta", {"name": "description"})
                or soup.find("meta", {"property": "og:description"})
                or soup.find("meta", {"name": "og:description"}))
        if meta and meta.get("content"):
            return short_summary_from_text(meta["content"])

        # Try first paragraph with real content
        for p in soup.find_all("p"):
            text = p.get_text(" ", strip=True)
            if len(text) >= 80:
                return short_summary_from_text(text)

        # Fallback: longest paragraph
        paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
        if paragraphs:
            longest = max(paragraphs, key=len)
            if len(longest) > 40:
                return short_summary_from_text(longest)
    except Exception:
        return ""
    return ""


def load_seen():
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_seen(seen):
    try:
        with open(SEEN_FILE, "w", encoding="utf-8") as f:
            json.dump(seen, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Error saving seen.json:", e)


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

                # Choose summary source
                cleaned_summary = re.sub("<[^<]+?>", "", raw_summary).strip()
                if cleaned_summary and len(cleaned_summary) >= 60:
                    summary_short = short_summary_from_text(cleaned_summary)
                else:
                    summary_short = fetch_page_summary(link) or short_summary_from_text(title)

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
        reel_idea = ""  # optional line for short creative idea

        entry = f"• {title}"
        if summary:
            entry += f"\n{summary}"
        entry += f"\n{link}"
        if reel_idea:
            entry += "\n" + reel_idea

        lines.append(entry)

    body = "\n\n".join(lines)
    msg = header + body
    if len(msg) > 3900:
        msg = msg[:3890] + "\n\n... (truncated)"
    return msg


def send_telegram(text):
    if not BOT_TOKEN or not CHAT_ID:
        raise RuntimeError("Missing BOT_TOKEN or CHAT_ID environment variables.")
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "disable_web_page_preview": True}
    r = requests.post(url, data=payload, timeout=20)
    r.raise_for_status()
    return r.json()


def main():
    try:
        items, new_guids = collect_items()
        msg = build_message(items)
        print("Sending message...")
        send_telegram(msg)
        print("Message sent.")
        if new_guids:
            seen = load_seen()
            seen.extend(new_guids)
            seen = seen[-2000:]
            save_seen(seen)
    except Exception as e:
        print("ERROR:", type(e).__name__, e)
        raise


if __name__ == "__main__":
    main()
