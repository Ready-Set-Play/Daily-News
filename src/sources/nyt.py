"""
nyt.py — New York Times source plugin.
Fetches Top Stories (per section) and Most Popular articles.
"""

import json
import logging
import os
import time
import urllib.error
import urllib.request

from .base import BaseSource

logger = logging.getLogger(__name__)


def _make_id(url: str, title: str) -> str:
    import hashlib

    return hashlib.sha256(f"{url}|{title}".encode()).hexdigest()[:16]


def _section_to_topic(section: str) -> str | None:
    mapping = {
        "technology": "technology",
        "science": "technology",
        "world": "world_events",
        "politics": "us_politics",
        "health": "technology",
        "arts": "culture",
    }
    return mapping.get(section)


def _extract_image(item: dict) -> str | None:
    multimedia = item.get("multimedia") or []
    for media in multimedia:
        if isinstance(media, dict) and media.get("format") == "thumpXLarge":
            return media.get("url")
    if multimedia and isinstance(multimedia[0], dict):
        return multimedia[0].get("url")
    return None


class Source(BaseSource):
    name = "nyt"
    requires_auth = True

    def fetch(self) -> list[dict]:
        api_key = os.environ.get(self.auth.get("api_key_env", "NYT_API_KEY"), "")
        base = self.config.get("base_url", "https://api.nytimes.com/svc")
        sections = self.config.get("sections", [])
        most_popular_days = self.config.get("most_popular_days", 7)

        articles = []

        for i, section in enumerate(sections):
            if i > 0:
                time.sleep(12)  # Delay between requests to prevent hitting rate limits (max 5/min)
            url = f"{base}/topstories/v2/{section}.json?api-key={api_key}"
            try:
                with urllib.request.urlopen(url, timeout=10) as resp:
                    data = json.loads(resp.read())
                for item in data.get("results") or []:
                    if not item.get("url"):
                        continue
                    articles.append(
                        {
                            "id": _make_id(item["url"], item.get("title", "")),
                            "title": item.get("title", ""),
                            "url": item["url"],
                            "source": "NYT",
                            "source_label": f"New York Times ({section.title()})",
                            "summary": item.get("abstract", ""),
                            "published": item.get("published_date", ""),
                            "topic_hint": _section_to_topic(section),
                            "image_url": _extract_image(item),
                            "is_nyt": True,
                        }
                    )
            except Exception as e:
                logger.warning(f"NYT top stories ({section}) failed: {e}")

        if sections:
            time.sleep(12)  # Delay before most popular request
        url = f"{base}/mostpopular/v2/shared/{most_popular_days}.json?api-key={api_key}"
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                data = json.loads(resp.read())
            for item in data.get("results") or []:
                if not item.get("url"):
                    continue
                articles.append(
                    {
                        "id": _make_id(item["url"], item.get("title", "")),
                        "title": item.get("title", ""),
                        "url": item["url"],
                        "source": "NYT",
                        "source_label": "New York Times (Most Popular)",
                        "summary": item.get("abstract", ""),
                        "published": item.get("published_date", ""),
                        "topic_hint": None,
                        "image_url": _extract_image(item),
                        "popularity_signal": True,
                        "is_nyt": True,
                    }
                )
        except Exception as e:
            logger.warning(f"NYT most popular failed: {e}")

        logger.info(f"NYT: fetched {len(articles)} articles")
        return articles
