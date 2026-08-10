import logging
import os
from datetime import datetime, timezone

import anthropic

logger = logging.getLogger(__name__)

_POST_ANGLES_PROMPT = """Based on the high-priority insurance news items below, suggest 3-4 concise LinkedIn post angles for Bharat Bima Insurance Broking.

Each angle should be one line — a hook or topic that would resonate with HR managers, CFOs, or business owners who buy group insurance. Focus on what's actionable or surprising.

Return just a numbered list, nothing else.

High-priority items:
{items}"""


def _extract_linkedin_items(summarized_content: str) -> list[str]:
    """Pull out item lines that are near a LinkedIn Signal: YES marker."""
    lines = summarized_content.split("\n")
    linkedin_items: list[str] = []

    for i, line in enumerate(lines):
        if "YES" in line and ("LinkedIn" in line or "Signal" in line):
            # grab the nearest preceding non-empty line as the item title
            for j in range(i - 1, max(i - 5, -1), -1):
                candidate = lines[j].strip()
                if candidate and not candidate.startswith("#"):
                    linkedin_items.append(candidate)
                    break

    # fallback: lines containing YES that look like content
    if not linkedin_items:
        linkedin_items = [
            line.strip()
            for line in lines
            if "YES" in line and len(line.strip()) > 15
        ]

    return linkedin_items[:8]


def _generate_post_angles(linkedin_items: list[str]) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key or not linkedin_items:
        return "- Review high-priority items above for post ideas."

    client = anthropic.Anthropic(api_key=api_key)
    items_text = "\n".join(f"- {item}" for item in linkedin_items)

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            messages=[{
                "role": "user",
                "content": _POST_ANGLES_PROMPT.format(items=items_text),
            }],
        )
        return message.content[0].text.strip()
    except anthropic.APIError as exc:
        logger.warning("Could not generate post angles: %s", exc)
        return "- Check high-priority items above for post ideas."


def format_digest(summarized_content: str, date: datetime) -> str:
    try:
        week_label = date.strftime("%d %b %Y").lstrip("0")
    except Exception:
        week_label = str(date)

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    linkedin_items = _extract_linkedin_items(summarized_content)
    post_angles = _generate_post_angles(linkedin_items)

    if linkedin_items:
        high_priority_section = "\n".join(f"- {item}" for item in linkedin_items)
    else:
        high_priority_section = "_No items flagged as LinkedIn-ready this week._"

    return f"""# Bharat Bima Weekly Insurance Digest — Week of {week_label}

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
