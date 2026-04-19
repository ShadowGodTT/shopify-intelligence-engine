import feedparser
import json
from datetime import datetime, timezone
from pathlib import Path

print("RUNNING NEW FETCH_RSS VERSION V3")

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
        "name": "Ad Hoc News Test Feed",
        "url": "https://www.ad-hoc-news.de/rss/nachrichten.xml"
    }
]

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
        title_key = article.get("title", "").strip().lower()
        link_key = article.get("link", "").split("?")[0].strip().lower()

        if not title_key or not link_key:
            continue

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
                title = getattr(entry, "title", "").strip()
                link = getattr(entry, "link", "").strip()

                print(f"Found article → {title}")

                article = {
                    "id": getattr(entry, "id", link),
                    "title": title,
                    "link": link,
                    "summary": getattr(entry, "summary", "").strip()[:1000],
                    "source": feed_source["name"],
                    "published": getattr(entry, "published", ""),
                    "fetched_at": datetime.now(timezone.utc).isoformat()
                }

                if title and link:
                    collected_articles.append(article)

        except Exception as error:
            print(f"Error fetching {feed_source['name']} → {error}")

    return collected_articles


# -----------------------------
# Main Runner
# -----------------------------

if __name__ == "__main__":
    print("Starting RSS fetch...")

    # Direct fresh fetch only (no old-state filtering)
    latest_articles = fetch_latest_articles()

    print(f"\nNew articles found → {len(latest_articles)}")

    # Deduplicate only current fetch
    cleaned_articles = deduplicate_articles(latest_articles)

    # Keep latest 500 max
    cleaned_articles = cleaned_articles[-500:]

    save_articles(cleaned_articles)

    print("RSS fetch completed successfully.")
