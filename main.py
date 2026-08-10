"""
Bharat Bima Weekly Insurance Digest — main entry point.

Usage:
    python main.py            # Full run: scrape, summarize, save, push to Sheets
    python main.py --dry-run  # Same but skip saving files and Sheets write
"""

import argparse
import logging
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv

from scraper.sources import SOURCES
from scraper.rss_fetcher import fetch_rss_items
from scraper.web_scraper import scrape_irdai
from processor.summarizer import summarize_items
from processor.formatter import format_digest
from output.digest_writer import save_digest
from output.sheets_writer import write_to_sheets

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")


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
                logger.warning("Unknown source type %s for %s", source["type"], source["name"])
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

    logger.info("=== Bharat Bima Weekly Digest — %s ===", now.strftime("%Y-%m-%d"))

    # 1. Collect
    logger.info("Collecting news from %d sources…", len(SOURCES))
    items = collect_items()
    logger.info("Total unique items collected: %d", len(items))

    if not items:
        logger.warning("No items collected — digest will be empty")

    # 2. Summarize
    logger.info("Summarizing with Claude…")
    summarized = summarize_items(items)

    # 3. Format
    logger.info("Formatting digest…")
    markdown = format_digest(summarized, now)

    if dry_run:
        print("\n--- DRY RUN — digest not saved ---\n")
        print(markdown[:3000])
        print("\n[truncated — full digest would be saved to digests/]")
        return

    # 4. Save to file
    save_digest(markdown, now)

    # 5. Push to Google Sheets
    write_to_sheets(items, summarized, markdown, now)

    print(f"\nDigest complete — {len(items)} items processed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bharat Bima Weekly Insurance Digest")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run pipeline without saving files or writing to Sheets",
    )
    args = parser.parse_args()
    main(dry_run=args.dry_run)
