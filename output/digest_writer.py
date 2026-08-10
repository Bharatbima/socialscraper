import logging
import os
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

DIGESTS_DIR = Path(__file__).parent.parent / "digests"


def save_digest(markdown_content: str, date: datetime) -> None:
    DIGESTS_DIR.mkdir(exist_ok=True)

    dated_filename = DIGESTS_DIR / f"{date.strftime('%Y-%m-%d')}-digest.md"
    latest_filename = DIGESTS_DIR / "latest.md"

    dated_filename.write_text(markdown_content, encoding="utf-8")
    logger.info("Digest saved to %s", dated_filename)

    latest_filename.write_text(markdown_content, encoding="utf-8")
    logger.info("Latest digest updated at %s", latest_filename)

    print(f"Digest saved: {dated_filename}")
    print(f"Latest digest updated: {latest_filename}")
