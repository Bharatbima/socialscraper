import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

_DIGESTS_DIR = Path(__file__).parent.parent / "digests"


def save_digest(markdown_content: str, date: datetime) -> None:
    _DIGESTS_DIR.mkdir(exist_ok=True)

    dated_file = _DIGESTS_DIR / f"{date.strftime('%Y-%m-%d')}-digest.md"
    latest_file = _DIGESTS_DIR / "latest.md"

    dated_file.write_text(markdown_content, encoding="utf-8")
    latest_file.write_text(markdown_content, encoding="utf-8")

    logger.info("Digest saved: %s", dated_file)
    logger.info("Latest digest updated: %s", latest_file)
    print(f"Digest saved: {dated_file}")
