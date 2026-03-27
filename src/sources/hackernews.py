"""
hackernews.py — Hacker News source plugin (Phase 3 reference implementation).
Uses the Algolia HN Search API — no auth required.
"""

import json
import logging
import urllib.request
import urllib.parse
from datetime import datetime, timezone

from .base import BaseSource, SourceFetchError

logger = logging.getLogger(__name__)


def _make_id(url: str, title: str) -> str:
    import hashlib

    return hashlib.sha256(f"{url}|{title}".encode()).hexdigest()[:16]


class Source(BaseSource):
    name = "hackernews"

    def fetch(self) -> list[dict]:
        min_score = self.config.get("min_score", 200)
        limit = self.config.get("limit", 20)

        # Algolia HN Search API — front page stories sorted by points
        params = urllib.parse.urlencode(
            {
                "tags": "front_page",
                "hitsPerPage": limit,
            }
        )
        url = f"https://hn.algolia.com/api/v1/search?{params}"

        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                data = json.loads(resp.read())
        except Exception as e:
            raise SourceFetchError(f"Hacker News fetch failed: {e}") from e

        articles = []
        for hit in data.get("hits", []):
            points = hit.get("points") or 0
            if points < min_score:
                continue
            story_url = (
                hit.get("url")
                or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}"
            )
            if not story_url:
                continue

            created_at = hit.get("created_at", "")
            try:
                pub_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                published = pub_dt.isoformat()
            except Exception:
                published = created_at

            articles.append(
                {
                    "id": _make_id(story_url, hit.get("title", "")),
                    "title": hit.get("title", ""),
                    "url": story_url,
                    "hn_url": f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}",
                    "source": "Hacker News",
                    "source_label": "Hacker News",
                    "summary": f"{points} points · {hit.get('num_comments', 0)} comments",
                    "published": published,
                    "topic_hint": "technology",
                    "image_url": None,
                    "hn_score": points,
                    "num_comments": hit.get("num_comments", 0),
                }
            )

        logger.info(
            f"Hacker News: fetched {len(articles)} stories (min_score={min_score})"
        )
        return articles
