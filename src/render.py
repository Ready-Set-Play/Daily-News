"""
render.py — Build the HTML email from selected, summarized articles.
"""

import os
from datetime import datetime, timezone
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")
CONFIG_DIR = os.path.join(os.path.dirname(__file__), "..", "config")
STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")


def _token_expiry_context() -> dict | None:
    """
    Returns expiry display data for the email footer, or None if suppressed/unconfigured.
    Reads GITHUB_TOKEN_EXPIRES (YYYY-MM-DD) and notifications.token_expiry_reminder from sources.yaml.
    """
    sources_path = os.path.join(CONFIG_DIR, "sources.yaml")
    if not os.path.exists(sources_path):
        sources_path = os.path.join(CONFIG_DIR, "sources.yaml.example")
    try:
        with open(sources_path) as f:
            sources_cfg = yaml.safe_load(f)
        enabled = sources_cfg.get("notifications", {}).get("token_expiry_reminder", True)
    except Exception:
        enabled = True

    if not enabled:
        return None

    expires_str = os.environ.get("GITHUB_TOKEN_EXPIRES", "").strip()
    if not expires_str:
        return None

    try:
        expiry_dt = datetime.strptime(expires_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None

    days = (expiry_dt - datetime.now(tz=timezone.utc)).days

    if days > 30:
        color = "#aaaaaa"
        urgency = "normal"
    elif days > 10:
        color = "#b86e00"
        urgency = "warning"
    else:
        color = "#b91c1c"
        urgency = "urgent"

    return {
        "date": expiry_dt.strftime("%B %-d, %Y"),
        "days_remaining": days,
        "color": color,
        "urgency": urgency,
    }




# Section ordering from topics.yaml
SECTION_ORDER: list[str] = []


def _load_section_order() -> list[dict]:
    path = os.path.join(CONFIG_DIR, "topics.yaml")
    if not os.path.exists(path):
        path = os.path.join(CONFIG_DIR, "topics.yaml.example")
    with open(path) as f:
        return yaml.safe_load(f)["sections"]


def group_by_topic(articles: list[dict]) -> list[dict]:
    """Group articles into topic sections, ordered by topics.yaml."""
    sections = _load_section_order()
    section_map = {s["id"]: {**s, "items": []} for s in sections}

    # Separate special items
    xkcd = None
    podcasts = []
    regular = []

    for a in articles:
        if a.get("is_xkcd"):
            xkcd = a
        elif a.get("is_podcast"):
            podcasts.append(a)
        else:
            regular.append(a)

    # Place regular articles into sections
    for a in regular:
        topic = a.get("ai_topic") or a.get("topic_hint", "")
        if topic in section_map:
            section_map[topic]["items"].append(a)
        else:
            # Default to technology if unrecognized
            section_map.get("technology", {"items": []})["items"].append(a)

    # Build ordered section list (only include sections with items)
    ordered = []
    for s in sections:
        section = section_map[s["id"]]
        if section["items"]:
            ordered.append(section)

    # Append podcasts section if any
    if podcasts:
        ordered.append(
            {
                "id": "podcasts",
                "label": "New Podcasts",
                "emoji": "🎙️",
                "items": podcasts,
            }
        )

    # Append XKCD last
    if xkcd:
        ordered.append(
            {
                "id": "xkcd",
                "label": "XKCD",
                "emoji": "😄",
                "items": [xkcd],
                "is_xkcd_section": True,
            }
        )

    return ordered


def render_email(articles: list[dict]) -> tuple[str, str]:
    """
    Render HTML and plain-text versions of the email.
    Returns (html_body, text_body).
    """
    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=True)
    template = env.get_template("digest.html")

    now = datetime.now(tz=timezone.utc)
    date_str = now.strftime("%A, %B %-d, %Y")  # e.g., "Sunday, March 22, 2026"

    sections = group_by_topic(articles)
    total_items = sum(len(s["items"]) for s in sections)
    has_nyt_content = any(a.get("is_nyt") for a in articles)

    html = template.render(
        date_str=date_str,
        sections=sections,
        total_items=total_items,
        has_nyt_content=has_nyt_content,
        token_expiry=_token_expiry_context(),
    )

    # Plain text fallback
    text = _render_plaintext(date_str, sections)

    return html, text


def _render_plaintext(date_str: str, sections: list[dict]) -> str:
    lines = [
        f"DAILY BRIEF — {date_str}",
        "=" * 50,
        "",
    ]
    for section in sections:
        lines.append(f"{section['emoji']} {section['label'].upper()}")
        lines.append("-" * 30)
        for item in section["items"]:
            lines.append(f"• {item['title']}")
            if item.get("tldr_summary"):
                lines.append(f"  {item['tldr_summary']}")
            lines.append(f"  {item['url']}")
            lines.append("")
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    import json
    import sys

    articles = json.load(sys.stdin)
    html, text = render_email(articles)
    print(html[:500])
    print("...")
