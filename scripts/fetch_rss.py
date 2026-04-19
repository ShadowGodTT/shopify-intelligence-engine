import feedparser
import json
from datetime import datetime, timezone
from pathlib import Path

# =====================================================
# Shopify Intelligence Engine
# File: scripts/fetch_rss.py
# Purpose:
# Fetch latest RSS updates
# Remove duplicates
# Save fresh articles into data/raw_articles.json
# =====================================================

# -----------------------------
# Reliable RSS Feed Sources
# -----------------------------

FEEDS = [
    {
        "name": "Shopify Developer Changelog",
        "url": "https://shopify.dev/changelog/feed"
    },
    {
        "name": "Shopify Editions",
        "url": "https://www.shopify.com/editions.atom"
    },
    {
        "name": "Ad Hoc News Test Feed",
        "url": "https://www.ad-hoc-news.de/rss/nachrichten.xml"
    }
]

# -----------------------------
# Settings
# -----------------------------

LOOKBACK_HOURS = 720  # currently not enforced


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
    collected_articles = []

    for feed_source in FEEDS:
        print(f"\nFetching → {feed_source['name']}")

        try:
            feed = feedparser.parse(feed_source["url"])

            print(f"Entries found → {len(feed.entries)}")

            if not feed.entries:
                print(f"No entries found for {feed_source['name']}")
                continue

            for entry in feed.entries:
                print(f"Found article → {getattr(entry, 'title', 'No Title')}")

                article = {
                    "id": getattr(entry, "id", getattr(entry, "link", "")),
                    "title": getattr(entry, "title", "").strip(),
                    "link": getattr(entry, "link", "").strip(),
                    "summary": getattr(entry, "summary", "").strip()[:1000],
                    "source": feed_source["name"],
                    "published": getattr(entry, "published", ""),
                    "fetched_at": datetime.now(timezone.utc).isoformat()
                }

                if article["title"] and article["link"]:
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
    existing_ids = {article.get("id", "") for article in existing_articles}

    latest_articles = fetch_latest_articles()

    fresh_articles = [
        article for article in latest_articles
        if article["id"] not in existing_ids
    ]

    print(f"\nNew articles found → {len(fresh_articles)}")

    merged_articles = existing_articles + fresh_articles
    merged_articles = deduplicate_articles(merged_articles)

    # Keep latest 500 records only
    cleaned_articles = merged_articles[-500:]

    save_articles(cleaned_articles)

    print("RSS fetch completed successfully.")
