import logging
from datetime import datetime

logger = logging.getLogger(__name__)

_ARTICLES_HEADERS = ["Date", "Source", "Title", "URL", "Summary", "Tags", "LinkedIn Signal", "Week"]
_DIGESTS_HEADERS = ["Date", "Item Count", "Digest Markdown"]

_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def _get_client():
    import google.auth
    import gspread

    creds, _ = google.auth.default(scopes=_SCOPES)
    return gspread.authorize(creds)


def _get_existing_urls(worksheet) -> set[str]:
    try:
        # URL is column D (index 3)
        url_col = worksheet.col_values(4)
        return set(url_col[1:])  # skip header row
    except Exception as exc:
        logger.warning("Could not fetch existing URLs for dedup: %s", exc)
        return set()


def _infer_linkedin_signal(item: dict, summarized_content: str) -> str:
    """Best-effort extraction of YES/NO signal from summarized content."""
    title_words = item.get("title", "").lower().split()[:4]
    if not title_words:
        return ""
    for line in summarized_content.split("\n"):
        line_lower = line.lower()
        if sum(1 for w in title_words if w in line_lower) >= 2:
            if "yes" in line_lower and ("linkedin" in line_lower or "signal" in line_lower):
                return "YES"
            if "no" in line_lower and ("linkedin" in line_lower or "signal" in line_lower):
                return "NO"
    return ""


def append_articles(items: list[dict], sheet_id: str, summarized_content: str = "") -> int:
    """
    Append new articles to the 'Articles' tab.
    Deduplicates by URL. Returns count of rows added.
    """
    try:
        gc = _get_client()
        ws = gc.open_by_key(sheet_id).worksheet("Articles")
    except Exception as exc:
        logger.error("Could not open Articles sheet: %s", exc)
        return 0

    try:
        # Write headers if sheet is empty
        if not ws.row_values(1):
            ws.append_row(_ARTICLES_HEADERS, value_input_option="RAW")

        existing_urls = _get_existing_urls(ws)
        week_label = f"Week of {datetime.now().strftime('%d %b %Y').lstrip('0')}"

        rows = []
        for item in items:
            url = item.get("url", "")
            if not url or url in existing_urls:
                continue
            existing_urls.add(url)
            rows.append([
                item.get("published_date", ""),
                item.get("source", ""),
                item.get("title", ""),
                url,
                item.get("summary", ""),
                ", ".join(item.get("tags", [])),
                _infer_linkedin_signal(item, summarized_content),
                week_label,
            ])

        if not rows:
            logger.info("No new articles to append (all duplicates)")
            return 0

        ws.append_rows(rows, value_input_option="RAW")
        logger.info("Appended %d new article rows to Sheets", len(rows))
        return len(rows)

    except Exception as exc:
        logger.error("Failed to append articles to Sheets: %s", exc)
        return 0


def append_digest(markdown: str, item_count: int, sheet_id: str) -> None:
    """
    Append one digest row to the 'Digests' tab.
    """
    try:
        gc = _get_client()
        ws = gc.open_by_key(sheet_id).worksheet("Digests")
    except Exception as exc:
        logger.error("Could not open Digests sheet: %s", exc)
        return

    try:
        if not ws.row_values(1):
            ws.append_row(_DIGESTS_HEADERS, value_input_option="RAW")

        row = [
            datetime.now().strftime("%Y-%m-%d"),
            item_count,
            markdown,
        ]
        ws.append_row(row, value_input_option="RAW")
        logger.info("Digest row written to Sheets")

    except Exception as exc:
        logger.error("Failed to append digest to Sheets: %s", exc)
