"""
Bharat Bima Weekly Insurance Digest

Usage:
    python main.py            # Full run
    python main.py --dry-run  # Skip saving files and Sheets write
"""

import argparse
import logging
import os
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv

from scraper.sources import SOURCES
from scraper.rss_fetcher import fetch_rss_items
from scraper.web_scraper import scrape_irdai
from processor.summarizer import summarize_items
from processor.formatter import format_digest
from output.digest_writer import save_digest
from output.sheets_writer import append_articles, append_digest

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")

DEFAULT_SHEET_ID = "1tz6ACayzo58uyzcJnr-37RHUbgCqE474OeCpoj21XIU"


def collect_items() -> list[dict]:
    all_items: list[dict] = []
    seen_urls: set[str] = set()

    for source in SOURCES:
        try:
            if source["type"] == "rss":
                items = fetch_rss_items(source)
            elif source["type"] == "scrape":
                items = scrape_irdai(source)
            else:
                logger.warning("Unknown source type '%s' for %s", source["type"], source["name"])
                continue
        except Exception as exc:
            logger.error("Unexpected error fetching %s: %s", source["name"], exc)
            continue

        for item in items:
            url = item.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                all_items.append(item)

    return all_items


def main(dry_run: bool = False) -> None:
    load_dotenv()
    now = datetime.now(timezone.utc)
    sheet_id = os.environ.get("GOOGLE_SHEET_ID", DEFAULT_SHEET_ID)

    logger.info("=== Bharat Bima Weekly Digest — %s ===", now.strftime("%Y-%m-%d"))
    if dry_run:
        logger.info("DRY RUN — no files or Sheets will be written")

    # 1. Collect
    logger.info("Collecting from %d sources…", len(SOURCES))
    items = collect_items()
    logger.info("Total unique items: %d", len(items))

    # 2. Summarize
    logger.info("Summarizing with Claude…")
    try:
        summarized = summarize_items(items)
    except Exception as exc:
        logger.error("Summarization failed: %s", exc)
        sys.exit(1)

    # 3. Format
    logger.info("Formatting digest…")
    markdown = format_digest(summarized, now)

    if dry_run:
        print("\n--- DRY RUN — digest preview (first 3000 chars) ---\n")
        print(markdown[:3000])
        print("\n--- End of preview ---")
        return

    # 4. Save to file
    save_digest(markdown, now)

    # 5. Write to Google Sheets (failures are logged, not raised)
    logger.info("Writing to Google Sheets…")
    added = append_articles(items, sheet_id, summarized)
    append_digest(markdown, len(items), sheet_id)
    print(f"Google Sheets: {added} new articles added.")

    print(f"\nDigest complete — {len(items)} items processed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bharat Bima Weekly Insurance Digest")
    parser.add_argument("--dry-run", action="store_true",
                        help="Run pipeline without saving files or writing to Sheets")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
