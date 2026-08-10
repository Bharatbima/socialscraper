import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

_ARTICLES_HEADERS = ["Date", "Source", "Title", "URL", "Summary", "Tags", "LinkedIn Signal", "Week"]
_DIGESTS_HEADERS = ["Date", "Item Count", "Digest Markdown"]


def _get_client():
    from google.oauth2.credentials import Credentials
    import gspread

    token = os.environ.get("GOOGLE_ACCESS_TOKEN")
    if not token:
        raise EnvironmentError("GOOGLE_ACCESS_TOKEN not set")

    creds = Credentials(token=token)
    return gspread.Client(auth=creds)


def _get_existing_urls(worksheet) -> set[str]:
    try:
        url_col = worksheet.col_values(4)  # Column D = URL
        return set(url_col[1:])            # skip header row
    except Exception as exc:
        logger.warning("Could not fetch existing URLs: %s", exc)
        return set()


def _infer_linkedin_signal(item: dict, summarized_content: str) -> str:
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
    try:
        gc = _get_client()
        ws = gc.open_by_key(sheet_id).worksheet("Articles")
        logger.info("Opened Articles sheet successfully")
    except Exception as exc:
        print(f"[SHEETS ERROR] Could not open Articles sheet: {exc}")
        logger.error("Could not open Articles sheet: %s", exc)
        return 0

    try:
        if not ws.row_values(1):
            ws.append_row(_ARTICLES_HEADERS, value_input_option="RAW")
            logger.info("Headers written to Articles sheet")

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
        logger.info("Appended %d article rows", len(rows))
        return len(rows)

    except Exception as exc:
        print(f"[SHEETS ERROR] Failed to append articles: {exc}")
        logger.error("Failed to append articles: %s", exc)
        return 0


def append_digest(markdown: str, item_count: int, sheet_id: str) -> None:
    try:
        gc = _get_client()
        ws = gc.open_by_key(sheet_id).worksheet("Digests")
        logger.info("Opened Digests sheet successfully")
    except Exception as exc:
        print(f"[SHEETS ERROR] Could not open Digests sheet: {exc}")
        logger.error("Could not open Digests sheet: %s", exc)
        return

    try:
        if not ws.row_values(1):
            ws.append_row(_DIGESTS_HEADERS, value_input_option="RAW")

        ws.append_row([
            datetime.now().strftime("%Y-%m-%d"),
            item_count,
            markdown,
        ], value_input_option="RAW")
        logger.info("Digest row written to Sheets")

    except Exception as exc:
        print(f"[SHEETS ERROR] Failed to append digest: {exc}")
        logger.error("Failed to append digest: %s", exc)
