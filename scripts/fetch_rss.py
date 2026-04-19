import feedparser
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

# =====================================================
# Shopify Intelligence Engine
# File: scripts/fetch_rss.py
# Purpose:
# Fetch latest Shopify RSS updates
# Remove duplicates
# Save fresh articles into data/raw_articles.json
# =====================================================

# -----------------------------
# RSS Feed Sources
# -----------------------------

FEEDS = [
    {
        "name": "Shopify Blog",
        "url": "https://www.shopify.com/blog.atom"
    },
    {
        "name": "Shopify Changelog",
        "url": "https://shopify.dev/changelog/feed"
    },
    {
        "name": "Shopify Developer Updates",
        "url": "https://shopify.dev/changelog/feed"
    }
]

# -----------------------------
# Settings
# -----------------------------

LOOKBACK_HOURS = 48


# -----------------------------
# Load Existing Articles
# -----------------------------

def load_existing_articles():
    path = Path("data/raw_articles.json")

    if path.exists():
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)

    return []


# -----------------------------
# Save Articles
# -----------------------------

def save_articles(articles):
    Path("data").mkdir(exist_ok=True)

    path = Path("data/raw_articles.json")

    with open(path, "w", encoding="utf-8") as file:
        json.dump(articles, file, indent=2, ensure_ascii=False)

    print(f"Saved {len(articles)} total articles → {path}")


# -----------------------------
# Deduplicate Articles
# -----------------------------

def deduplicate_articles(articles):
    seen_titles = set()
    seen_links = set()
    unique_articles = []

    for article in articles:
        title_key = article["title"].strip().lower()
        link_key = article["link"].split("?")[0].strip().lower()

        if title_key not in seen_titles and link_key not in seen_links:
            seen_titles.add(title_key)
            seen_links.add(link_key)
            unique_articles.append(article)

    return unique_articles


# -----------------------------
# Fetch Latest Articles
# -----------------------------

def fetch_latest_articles():
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)
    collected_articles = []

    for feed_source in FEEDS:
        print(f"Fetching → {feed_source['name']}")

        try:
            feed = feedparser.parse(feed_source["url"])

            for entry in feed.entries:
                published = None

                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    published = datetime(
                        *entry.published_parsed[:6],
                        tzinfo=timezone.utc
                    )

                elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                    published = datetime(
                        *entry.updated_parsed[:6],
                        tzinfo=timezone.utc
                    )

                if not published:
                    continue

                if published < cutoff_time:
                    continue

                article = {
                    "id": getattr(entry, "id", entry.link),
                    "title": getattr(entry, "title", "").strip(),
                    "link": getattr(entry, "link", "").strip(),
                    "summary": getattr(entry, "summary", "").strip()[:1000],
                    "source": feed_source["name"],
                    "published": published.isoformat(),
                    "fetched_at": datetime.now(timezone.utc).isoformat()
                }

                collected_articles.append(article)

        except Exception as error:
            print(f"Error fetching {feed_source['name']} → {error}")

    return collected_articles


# -----------------------------
# Main Runner
# -----------------------------

if __name__ == "__main__":
    print("Starting RSS fetch...")

    existing_articles = load_existing_articles()
    existing_ids = {article["id"] for article in existing_articles}

    latest_articles = fetch_latest_articles()

    fresh_articles = [
        article for article in latest_articles
        if article["id"] not in existing_ids
    ]

    print(f"New articles found → {len(fresh_articles)}")

    merged_articles = existing_articles + fresh_articles
    merged_articles = deduplicate_articles(merged_articles)

    cutoff = datetime.now(timezone.utc) - timedelta(hours=48)

    cleaned_articles = [
        article for article in merged_articles
        if datetime.fromisoformat(article["fetched_at"]) > cutoff
    ]

    save_articles(cleaned_articles)

    print("RSS fetch completed successfully.")
