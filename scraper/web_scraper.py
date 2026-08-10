import logging
import time
from datetime import datetime, timezone, timedelta

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_SEVEN_DAYS_AGO = datetime.now(timezone.utc) - timedelta(days=7)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-IN,en;q=0.9",
}


def _parse_irdai_date(text: str) -> datetime | None:
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%B %d, %Y", "%d %B %Y"):
        try:
            return datetime.strptime(text.strip(), fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def scrape_irdai(source: dict) -> list[dict]:
    url = source["url"]
    name = source["name"]
    tags = source.get("tags", [])

    time.sleep(2)

    try:
        resp = requests.get(url, headers=_HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.error("Failed to scrape %s: %s", name, exc)
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    items: list[dict] = []
    seen_urls: set[str] = set()

    rows = (
        soup.select("table tr")
        or soup.select("ul.list-group li")
        or soup.select("div.view-content .views-row")
    )

    for row in rows:
        link_tag = row.find("a", href=True)
        if not link_tag:
            continue

        title = link_tag.get_text(strip=True)
        href = link_tag["href"]
        if href.startswith("/"):
            href = "https://irdai.gov.in" + href
        if not href or href in seen_urls:
            continue
        seen_urls.add(href)

        date_text = ""
        for td in row.find_all(["td", "span", "div"]):
            text = td.get_text(strip=True)
            if "/" in text or "-" in text:
                date_text = text
                break

        pub_date = _parse_irdai_date(date_text) if date_text else None
        if pub_date and pub_date < _SEVEN_DAYS_AGO:
            continue

        items.append({
            "source": name,
            "title": title,
            "url": href,
            "published_date": pub_date.isoformat() if pub_date else "",
            "summary": "",
            "tags": tags,
        })

    logger.info("Scraped %d items from %s", len(items), name)
    return items
