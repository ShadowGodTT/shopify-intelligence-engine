import feedparser
import requests
import json
from datetime import datetime, timezone
from pathlib import Path

print("RUNNING FETCH_RSS VERSION V4")

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


def save_articles(articles):
    Path("data").mkdir(exist_ok=True)

    with open("data/raw_articles.json", "w", encoding="utf-8") as f:
        json.dump(articles, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(articles)} articles")


def deduplicate_articles(articles):
    seen = set()
    unique = []

    for article in articles:
        key = (
            article.get("title", "").strip().lower(),
            article.get("link", "").strip().lower()
        )

        if key not in seen and key[0] and key[1]:
            seen.add(key)
            unique.append(article)

    return unique


def fetch_latest_articles():
    collected_articles = []

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    for feed_source in FEEDS:
        print(f"\nFetching → {feed_source['name']}")

        try:
            response = requests.get(
                feed_source["url"],
                headers=headers,
                timeout=30
            )

            print(f"HTTP Status → {response.status_code}")

            if response.status_code != 200:
                print("Skipping due to bad response")
                continue

            feed = feedparser.parse(response.text)

            print(f"Entries found → {len(feed.entries)}")

            for entry in feed.entries:
                title = getattr(entry, "title", "").strip()
                link = getattr(entry, "link", "").strip()

                print(f"Found → {title}")

                if not title or not link:
                    continue

                article = {
                    "id": getattr(entry, "id", link),
                    "title": title,
                    "link": link,
                    "summary": getattr(entry, "summary", "")[:1000],
                    "source": feed_source["name"],
                    "published": getattr(entry, "published", ""),
                    "fetched_at": datetime.now(timezone.utc).isoformat()
                }

                collected_articles.append(article)

        except Exception as e:
            print(f"Error → {str(e)}")

    return collected_articles


if __name__ == "__main__":
    print("Starting RSS fetch...")

    latest_articles = fetch_latest_articles()

    print(f"\nRaw articles fetched → {len(latest_articles)}")

    cleaned_articles = deduplicate_articles(latest_articles)

    print(f"After dedupe → {len(cleaned_articles)}")

    save_articles(cleaned_articles)

    print("RSS fetch completed successfully.")
