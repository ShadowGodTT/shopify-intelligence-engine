import feedparser
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_VERSION = "V4-DIAGNOSTIC"
print(f"RUNNING fetch_rss.py {SCRIPT_VERSION}")
print(f"Python: {sys.version}")
print(f"feedparser: {feedparser.__version__}")

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
    path = Path("data/raw_articles.json")
    with open(path, "w", encoding="utf-8") as file:
        json.dump(articles, file, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(articles)} total articles → {path}")


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


def fetch_latest_articles():
    collected_articles = []

    for feed_source in FEEDS:
        name = feed_source["name"]
        url = feed_source["url"]

        print(f"\n{'='*60}")
        print(f"Fetching → {name}")
        print(f"URL      → {url}")

        try:
            feed = feedparser.parse(url)

            # CRITICAL: Always log these — they reveal silent failures
            http_status = getattr(feed, "status", "NO_STATUS")
            bozo = getattr(feed, "bozo", False)
            bozo_exc = getattr(feed, "bozo_exception", None)
            feed_title = getattr(feed.feed, "title", "NO_FEED_TITLE")
            content_type = feed.get("headers", {}).get("content-type", "UNKNOWN")

            print(f"HTTP Status      → {http_status}")
            print(f"Feed Title       → {feed_title}")
            print(f"Content-Type     → {content_type}")
            print(f"Bozo (malformed) → {bozo}")
            if bozo and bozo_exc:
                print(f"Bozo Exception   → {type(bozo_exc).__name__}: {bozo_exc}")
            print(f"Entries found    → {len(feed.entries)}")

            if http_status == 301 or http_status == 302:
                redirect = feed.get("href", "UNKNOWN")
                print(f"WARNING: Feed redirected to → {redirect}")
                print(f"         Update the URL in FEEDS config to avoid redirect overhead.")

            if not feed.entries:
                print(f"RESULT: 0 entries — feed parsed but returned nothing.")
                # Dump raw feed keys so we can see what came back
                print(f"Feed keys available: {list(feed.feed.keys())[:20]}")
                continue

            for entry in feed.entries:
                title = getattr(entry, "title", "").strip()
                link = getattr(entry, "link", "").strip()

                if not title or not link:
                    print(f"  SKIP: Missing title or link — title={repr(title)}, link={repr(link)}")
                    continue

                print(f"  + {title[:80]}")

                article = {
                    "id": getattr(entry, "id", link),
                    "title": title,
                    "link": link,
                    "summary": getattr(entry, "summary", "").strip()[:1000],
                    "source": name,
                    "published": getattr(entry, "published", ""),
                    "fetched_at": datetime.now(timezone.utc).isoformat()
                }

                collected_articles.append(article)

        except Exception as error:
            print(f"EXCEPTION fetching {name} → {type(error).__name__}: {error}")

    return collected_articles


if __name__ == "__main__":
    print("\nStarting RSS fetch...")

    latest_articles = fetch_latest_articles()

    print(f"\n{'='*60}")
    print(f"Total raw articles collected → {len(latest_articles)}")

    cleaned_articles = deduplicate_articles(latest_articles)
    print(f"After deduplication          → {len(cleaned_articles)}")

    cleaned_articles = cleaned_articles[-500:]

    save_articles(cleaned_articles)

    print("\nRSS fetch completed.")

    # Exit non-zero if 0 articles — makes the GitHub Actions step visibly RED
    # so you can't miss it. Comment this out if you want the pipeline to
    # continue even on 0 articles.
    if len(cleaned_articles) == 0:
        print("\nFATAL: 0 articles fetched. Check feed URLs and HTTP status above.")
        sys.exit(1)
