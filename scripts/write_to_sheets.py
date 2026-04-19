import json
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from pathlib import Path

# =====================================================
# Shopify Intelligence Engine
# File: scripts/write_to_sheets.py
# Purpose:
# Read events.json
# Connect to Google Sheets
# Write structured events into Events Database tab
# =====================================================

# -----------------------------
# Config
# -----------------------------

SHEET_NAME = "Shopify Intelligence Dashboard"
WORKSHEET_NAME = "Events Database"

GOOGLE_SERVICE_ACCOUNT_JSON = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")

# -----------------------------
# Google Sheets Auth
# -----------------------------

def get_google_client():
    if not GOOGLE_SERVICE_ACCOUNT_JSON:
        raise ValueError("Missing GOOGLE_SERVICE_ACCOUNT_JSON in environment variables")

    credentials_dict = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)

    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]

    credentials = ServiceAccountCredentials.from_json_keyfile_dict(
        credentials_dict,
        scope
    )

    client = gspread.authorize(credentials)
    return client


# -----------------------------
# Load Events
# -----------------------------

def load_events():
    path = Path("data/events.json")

    if not path.exists():
        print("No events.json found.")
        return []

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


# -----------------------------
# Format Rows
# -----------------------------

def format_rows(events):
    rows = []

    for event in events:
        row = [
            event.get("date", ""),
            event.get("event_title", ""),
            event.get("summary", ""),
            event.get("merchant_impact", ""),
            event.get("category", ""),
            event.get("reliability_score", ""),
            event.get("reliability_reason", ""),
            ", ".join(event.get("sources", [])),
            ", ".join(event.get("citations", [])),
            event.get("status", "New"),
            event.get("content_angle", ""),
            event.get("priority", "Medium"),
            event.get("event_id", ""),
            event.get("date", "")
        ]

        rows.append(row)

    return rows


# -----------------------------
# Write to Google Sheets
# -----------------------------

def write_to_google_sheets(rows):
    client = get_google_client()

    sheet = client.open(SHEET_NAME)
    worksheet = sheet.worksheet(WORKSHEET_NAME)

    # Clear old data except header row
    if worksheet.row_count > 1:
        worksheet.batch_clear(["A2:N1000"])

    if rows:
        worksheet.append_rows(rows, value_input_option="RAW")
        print(f"Successfully wrote {len(rows)} rows to Google Sheets")
    else:
        print("No rows to write")


# -----------------------------
# Main Runner
# -----------------------------

if __name__ == "__main__":
    print("Starting Google Sheets update...")

    events = load_events()

    if not events:
        print("No events available.")
        exit()

    print(f"Loaded {len(events)} events")

    rows = format_rows(events)

    write_to_google_sheets(rows)

    print("Google Sheets update completed successfully.")
