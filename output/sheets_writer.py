import json
import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Column layout for the Articles sheet (1-indexed for Sheets API)
ARTICLES_HEADERS = [
    "Date", "Week", "Source", "Title", "URL",
    "Summary", "Tags", "LinkedIn Signal",
]

# Column layout for the Digests sheet
DIGESTS_HEADERS = ["Date", "Week", "Item Count", "Digest Markdown"]


def _get_sheets_service():
    """Build and return an authenticated Google Sheets service client."""
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build

    creds_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not creds_json:
        raise EnvironmentError("GOOGLE_SERVICE_ACCOUNT_JSON env var not set")

    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    return build("sheets", "v4", credentials=creds, cache_discovery=False)


def _ensure_headers(service, spreadsheet_id: str, sheet_name: str, headers: list[str]) -> None:
    """Write headers to row 1 if the sheet is empty."""
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=f"{sheet_name}!A1:A1")
        .execute()
    )
    if not result.get("values"):
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"{sheet_name}!A1",
            valueInputOption="RAW",
            body={"values": [headers]},
        ).execute()
        logger.info("Headers written to %s sheet", sheet_name)


def _get_existing_urls(service, spreadsheet_id: str) -> set[str]:
    """Return all URLs already in the Articles sheet to deduplicate."""
    try:
        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range="Articles!E:E")
            .execute()
        )
        rows = result.get("values", [])
        return {row[0] for row in rows if row}
    except Exception as exc:
        logger.warning("Could not fetch existing URLs: %s", exc)
        return set()


def _extract_linkedin_signal(item: dict, summarized_content: str) -> str:
    """Try to infer the LinkedIn signal for an item from the summarized content."""
    title = item.get("title", "").lower()
    if not title:
        return ""
    # Look for the title (or a fragment) near a YES/NO signal in the summary
    for line in summarized_content.split("\n"):
        if any(word in line.lower() for word in title.split()[:3]):
            if "YES" in line:
                return "YES"
            if "NO" in line:
                return "NO"
    return ""


def write_articles_to_sheets(
    items: list[dict],
    summarized_content: str,
    spreadsheet_id: str,
    week_label: str,
) -> int:
    """Append new articles to the Articles sheet. Returns count of rows added."""
    try:
        service = _get_sheets_service()
    except Exception as exc:
        logger.error("Google Sheets auth failed: %s", exc)
        return 0

    try:
        _ensure_headers(service, spreadsheet_id, "Articles", ARTICLES_HEADERS)
        existing_urls = _get_existing_urls(service, spreadsheet_id)

        rows = []
        for item in items:
            url = item.get("url", "")
            if url in existing_urls:
                continue
            existing_urls.add(url)

            linkedin_signal = _extract_linkedin_signal(item, summarized_content)
            rows.append(
                [
                    item.get("published_date", ""),
                    week_label,
                    item.get("source", ""),
                    item.get("title", ""),
                    url,
                    item.get("summary", ""),
                    ", ".join(item.get("tags", [])),
                    linkedin_signal,
                ]
            )

        if not rows:
            logger.info("No new articles to add to Sheets (all duplicates)")
            return 0

        service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range="Articles!A1",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": rows},
        ).execute()

        logger.info("Added %d new article rows to Sheets", len(rows))
        return len(rows)

    except Exception as exc:
        logger.error("Failed to write articles to Sheets: %s", exc)
        return 0


def write_digest_to_sheets(
    markdown_content: str,
    item_count: int,
    spreadsheet_id: str,
    date: datetime,
    week_label: str,
) -> None:
    """Append one digest row to the Digests sheet."""
    try:
        service = _get_sheets_service()
    except Exception as exc:
        logger.error("Google Sheets auth failed: %s", exc)
        return

    try:
        _ensure_headers(service, spreadsheet_id, "Digests", DIGESTS_HEADERS)

        row = [
            date.strftime("%Y-%m-%d"),
            week_label,
            item_count,
            markdown_content,
        ]

        service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range="Digests!A1",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": [row]},
        ).execute()

        logger.info("Digest row written to Sheets")

    except Exception as exc:
        logger.error("Failed to write digest to Sheets: %s", exc)


def write_to_sheets(
    items: list[dict],
    summarized_content: str,
    markdown_content: str,
    date: datetime,
) -> None:
    """Main entry point: write articles + digest to Google Sheets."""
    spreadsheet_id = os.environ.get("GOOGLE_SHEET_ID")
    if not spreadsheet_id:
        logger.warning("GOOGLE_SHEET_ID not set — skipping Sheets export")
        return

    week_label = f"Week of {date.strftime('%d %b %Y').lstrip('0')}"

    added = write_articles_to_sheets(items, summarized_content, spreadsheet_id, week_label)
    write_digest_to_sheets(markdown_content, len(items), spreadsheet_id, date, week_label)

    print(f"Google Sheets: {added} new articles added, digest logged.")
