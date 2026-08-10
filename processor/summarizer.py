import logging
import os

import anthropic

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a research assistant for Bharat Bima Insurance Broking, a direct insurance broker in India licensed by IRDAI.

Your job is to read a list of raw news headlines and summaries from the past week, and produce a clean, structured weekly digest for the leadership team.

For each news item, write:
- A one-line plain-English summary (what happened and why it matters for insurance brokers or their clients)
- A relevance tag: [IRDAI] [Group Health] [Group Life] [MFI] [Market] [Regulation] [Claims] [Product]
- A LinkedIn signal: YES or NO — whether this item could anchor a LinkedIn post

Return the digest as structured markdown. Be concise. Cut anything that is generic filler or not relevant to Indian insurance broking."""

THEME_GROUPS = {
    "Regulation & IRDAI": ["IRDAI", "Regulation"],
    "Group Health & Life": ["Group Health", "Group Life"],
    "MFI & Microfinance": ["MFI", "Microfinance"],
    "Market & Industry": ["Market", "Industry"],
    "Other": [],
}


def _group_by_theme(items: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {theme: [] for theme in THEME_GROUPS}
    for item in items:
        item_tags = set(item.get("tags", []))
        placed = False
        for theme, theme_tags in THEME_GROUPS.items():
            if theme_tags and item_tags.intersection(theme_tags):
                grouped[theme].append(item)
                placed = True
                break
        if not placed:
            grouped["Other"].append(item)
    return grouped


def _build_user_message(items: list[dict]) -> str:
    grouped = _group_by_theme(items)
    lines = ["Here are this week's news items grouped by theme:\n"]
    for theme, theme_items in grouped.items():
        if not theme_items:
            continue
        lines.append(f"### {theme}")
        for i, item in enumerate(theme_items, 1):
            lines.append(f"{i}. **{item['title']}**")
            lines.append(f"   Source: {item['source']} | Date: {item.get('published_date', 'unknown')}")
            if item.get("summary"):
                lines.append(f"   Summary: {item['summary']}")
            lines.append(f"   URL: {item['url']}")
            lines.append("")
    return "\n".join(lines)


def summarize_items(items: list[dict]) -> str:
    if not items:
        return "No items to summarize this week."

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not set — cannot summarize")
        return "Error: ANTHROPIC_API_KEY not configured."

    client = anthropic.Anthropic(api_key=api_key)
    user_message = _build_user_message(items)

    logger.info("Sending %d items to Claude for summarization", len(items))
    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        result = message.content[0].text
        logger.info("Summarization complete — %d chars returned", len(result))
        return result
    except anthropic.APIError as exc:
        logger.error("Anthropic API error: %s", exc)
        raise
