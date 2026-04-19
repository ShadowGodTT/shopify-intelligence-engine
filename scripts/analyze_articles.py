import json
import os
import requests
from datetime import datetime, timezone
from pathlib import Path

# =====================================================
# Shopify Intelligence Engine
# File: scripts/analyze_articles.py
# Purpose:
# Read raw_articles.json
# Send articles to Groq AI
# Get structured strategic insights
# Save output into data/events.json
# =====================================================

# -----------------------------
# Config
# -----------------------------

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"

MODEL = "llama3-70b-8192"

MAX_ARTICLES_PER_BATCH = 10
TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")


# -----------------------------
# Prompt
# -----------------------------

SYSTEM_PROMPT = """
You are a senior analyst monitoring the Shopify ecosystem for Project Supply.

Your job is to analyze Shopify-related articles and return ONLY high-value strategic events.

You must:

1. FILTER:
Only keep articles about:
- Shopify platform changes
- checkout updates
- payments
- subscriptions
- retention
- AI + automation
- B2B commerce
- apps ecosystem
- merchant growth opportunities

2. DEDUPLICATE:
Merge articles talking about the same event.

3. ANALYZE:
For each valid event, explain:
- what happened
- why it matters
- merchant impact
- strategic publishing opportunity

Return ONLY valid JSON array.
No markdown.
No explanation.
No backticks.
No extra text.
"""

USER_PROMPT_TEMPLATE = """
Today is {today}.

Analyze these {count} Shopify articles:

{articles}

Return JSON array using this exact schema:

[
  {{
    "event_id": "EVT-001",
    "date": "YYYY-MM-DD",
    "event_title": "Clear factual headline",
    "summary": "2-3 sentence explanation of what happened",
    "merchant_impact": "1-2 sentences explaining merchant impact",
    "category": "Platform Update | Checkout | Payments | AI | Apps | Retention | Subscription | B2B",
    "reliability_score": 1-10,
    "reliability_reason": "Short reason for the score",
    "sources": ["Source 1", "Source 2"],
    "citations": ["url1", "url2"],
    "status": "New",
    "content_angle": "Suggested article or social post angle",
    "priority": "High | Medium | Low"
  }}
]
"""


# -----------------------------
# Load Articles
# -----------------------------

def load_articles():
    path = Path("data/raw_articles.json")

    if not path.exists():
        print("No raw_articles.json found.")
        return []

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


# -----------------------------
# Call Groq API
# -----------------------------

def call_groq(batch):
    articles_text = "\n\n".join([
        f"""
SOURCE: {article.get("source", "")}
TITLE: {article.get("title", "")}
URL: {article.get("link", "")}
SUMMARY: {article.get("summary", "")}
"""
        for article in batch
    ])

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": USER_PROMPT_TEMPLATE.format(
                    today=TODAY,
                    count=len(batch),
                    articles=articles_text
                )
            }
        ],
        "temperature": 0.2,
        "max_tokens": 4000
    }

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.post(
        GROQ_ENDPOINT,
        headers=headers,
        json=payload,
        timeout=60
    )

    response.raise_for_status()

    raw_output = response.json()["choices"][0]["message"]["content"].strip()

    # Cleanup accidental markdown formatting
    if raw_output.startswith("```"):
        raw_output = raw_output.split("\n", 1)[1]
        raw_output = raw_output.rsplit("```", 1)[0]

    return json.loads(raw_output)


# -----------------------------
# Deduplicate Events
# -----------------------------

def deduplicate_events(events):
    seen = {}
    final_events = []

    for event in events:
        key = event["event_title"].strip().lower()

        if key not in seen:
            seen[key] = event
            final_events.append(event)

    return final_events


# -----------------------------
# Save Events
# -----------------------------

def save_events(events):
    Path("data").mkdir(exist_ok=True)

    path = Path("data/events.json")

    with open(path, "w", encoding="utf-8") as file:
        json.dump(events, file, indent=2, ensure_ascii=False)

    print(f"Saved {len(events)} events → {path}")


# -----------------------------
# Main Runner
# -----------------------------

if __name__ == "__main__":
    print("Starting AI analysis...")

    if not GROQ_API_KEY:
        raise ValueError("Missing GROQ_API_KEY in environment variables")

    articles = load_articles()

    if not articles:
        print("No articles available for analysis.")
        exit()

    print(f"Loaded {len(articles)} articles")

    all_events = []

    for i in range(0, len(articles), MAX_ARTICLES_PER_BATCH):
        batch = articles[i:i + MAX_ARTICLES_PER_BATCH]

        print(f"Analyzing batch {i//MAX_ARTICLES_PER_BATCH + 1}...")

        try:
            events = call_groq(batch)
            all_events.extend(events)

        except Exception as error:
            print(f"Error analyzing batch: {error}")

    final_events = deduplicate_events(all_events)

    save_events(final_events)

    print("AI analysis completed successfully.")
