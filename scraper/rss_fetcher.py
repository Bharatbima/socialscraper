import logging
from datetime import datetime, timezone, timedelta

import feedparser

logger = logging.getLogger(__name__)

_SEVEN_DAYS_AGO = datetime.now(timezone.utc) - timedelta(days=7)


def _parse_date(entry) -> datetime | None:
    for attr in ("published_parsed", "updated_parsed"):
        t = getattr(entry, attr, None)
        if t:
            try:
                return datetime(*t[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    return None


def _strip_html(text: str) -> str:
    try:
        from bs4 import BeautifulSoup
        return BeautifulSoup(text, "lxml").get_text(separator=" ").strip()
    except Exception:
        return text


def fetch_rss_items(source: dict) -> list[dict]:
    url = source["url"]
    name = source["name"]
    tags = source.get("tags", [])

    try:
        feed = feedparser.parse(url)
        if feed.bozo and not feed.entries:
            logger.warning("Feed parse error for %s: %s", name, feed.bozo_exception)
            return []
    except Exception as exc:
        logger.error("Failed to fetch RSS feed %s: %s", name, exc)
        return []

    seen_urls: set[str] = set()
    items: list[dict] = []

    for entry in feed.entries:
        link = getattr(entry, "link", "").strip()
        if not link or link in seen_urls:
            continue
        seen_urls.add(link)

        pub_date = _parse_date(entry)
        if pub_date and pub_date < _SEVEN_DAYS_AGO:
            continue

        title = getattr(entry, "title", "").strip()
        summary = _strip_html(getattr(entry, "summary", "").strip())

        items.append({
            "source": name,
            "title": title,
            "url": link,
            "published_date": pub_date.isoformat() if pub_date else "",
            "summary": summary[:500],
            "tags": tags,
        })

    logger.info("Fetched %d items from %s", len(items), name)
    return items
