import logging
import os
from datetime import datetime, timezone

import anthropic

logger = logging.getLogger(__name__)

POST_ANGLES_PROMPT = """Based on the high-priority insurance news items below, suggest 3-4 concise LinkedIn post angles for Bharat Bima Insurance Broking.

Each angle should be one line: a hook or topic that would work as a post. Think: what would resonate with HR managers, CFOs, or business owners who buy group insurance?

Return just a numbered list, nothing else.

High-priority items:
{items}"""


def _extract_linkedin_items(summarized_content: str) -> list[str]:
    lines = summarized_content.split("\n")
    linkedin_items = []
    current_item_lines: list[str] = []
    capture = False

    for line in lines:
        if "LinkedIn signal: YES" in line or "LinkedIn Signal: YES" in line:
            capture = True
        if capture and line.strip().startswith(("- ", "* ", "1.", "2.", "3.", "4.", "5.")):
            if current_item_lines:
                linkedin_items.append(" ".join(current_item_lines).strip())
                current_item_lines = []
            current_item_lines.append(line.strip())
        elif capture and current_item_lines and line.strip():
            current_item_lines.append(line.strip())
        elif capture and not line.strip() and current_item_lines:
            linkedin_items.append(" ".join(current_item_lines).strip())
            current_item_lines = []
            capture = False

    if current_item_lines:
        linkedin_items.append(" ".join(current_item_lines).strip())

    # Fallback: grab lines that mention YES
    if not linkedin_items:
        linkedin_items = [
            line.strip()
            for line in lines
            if "YES" in line and len(line.strip()) > 10
        ]

    return linkedin_items[:8]


def _generate_post_angles(linkedin_items: list[str]) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key or not linkedin_items:
        return "- Review high-priority items above for post ideas"

    client = anthropic.Anthropic(api_key=api_key)
    items_text = "\n".join(f"- {item}" for item in linkedin_items)

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            messages=[
                {
                    "role": "user",
                    "content": POST_ANGLES_PROMPT.format(items=items_text),
                }
            ],
        )
        return message.content[0].text.strip()
    except anthropic.APIError as exc:
        logger.warning("Could not generate post angles: %s", exc)
        return "- Check high-priority items above for post ideas"


def format_digest(summarized_content: str, date: datetime) -> str:
    week_label = date.strftime("%-d %b %Y") if hasattr(date, "strftime") else str(date)
    # Windows-safe date formatting
    try:
        week_label = date.strftime("%d %b %Y").lstrip("0")
    except Exception:
        week_label = str(date)

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    linkedin_items = _extract_linkedin_items(summarized_content)
    post_angles = _generate_post_angles(linkedin_items)

    high_priority_section = ""
    if linkedin_items:
        high_priority_section = "\n".join(f"- {item}" for item in linkedin_items)
    else:
        high_priority_section = "_No items flagged as LinkedIn-ready this week._"

    digest = f"""# Bharat Bima Weekly Insurance Digest — Week of {week_label}

---

## 🔴 High Priority (LinkedIn Ready)

{high_priority_section}

---

## 📋 Full Week's News

{summarized_content}

---

## 💡 Suggested Post Angles

{post_angles}

---

_Generated: {generated_at}_
"""
    return digest
