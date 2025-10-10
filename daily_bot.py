import os
import json
import requests
import feedparser
from datetime import datetime, timedelta, timezone
import re
from bs4 import BeautifulSoup

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
MAX_ITEMS = 8
SEEN_FILE = "seen.json"
REQUEST_TIMEOUT = 8  # seconds

# --- summary helpers ---
def short_summary_from_text(text, max_chars=220, max_sentences=2):
    if not text:
        return ""
    text = re.sub('<[^<]+?>', '', text).strip()
    text = re.sub(r'\s+', ' ', text)
    sentences = re.split(r'(?<=[.!?])\s+', text)
    if len(sentences) >= 1:
        summary = ' '.join(sentences[:max_sentences]).strip()
    else:
        summary = text[:max_chars]
    if len(summary) > max_chars:
        summary = summary[:max_chars].rsplit(' ', 1)[0] + "..."
    return summary

def fetch_page_summary(url):
    """Fetches page and returns a short summary from meta description or first sizable <p>."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; Bot/1.0; +https://example.com/bot)"}
        r = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        html = r.text
        soup = BeautifulSoup(html, "html.parser")
        # 1) try meta description tags
        meta = (soup.find("meta", {"name":"description"}) or
                soup.find("meta", {"property":"og:description"}) or
                soup.find("meta", {"name":"og:description"}))
        if meta and meta.get("content"):
            return short_summary_from_text(meta.get("content"))
        # 2) try first mean
