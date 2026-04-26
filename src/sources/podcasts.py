"""
podcasts.py — Podcast RSS source plugin.
Fetches the latest episode from each configured podcast feed.
"""

import logging
import re
from datetime import datetime, timedelta, timezone

import feedparser

from .base import BaseSource, SourceFetchError

logger = logging.getLogger(__name__)


def _make_id(url: str, title: str) -> str:
    import hashlib

    return hashlib.sha256(f"{url}|{title}".encode()).hexdigest()[:16]


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()


class Source(BaseSource):
    name = "podcasts"

    def fetch(self) -> list[dict]:
        feeds = self.config.get("feeds", [])
        max_age_hours = self.config.get("max_age_hours", 48)
        cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=max_age_hours)

        articles = []

        for podcast in feeds:
            try:
                feed = feedparser.parse(podcast["url"])
                if not feed.entries:
                    continue
                entry = feed.entries[0]

                published_struct = entry.get("published_parsed") or entry.get(
                    "updated_parsed"
                )
                if published_struct:
                    pub_dt = datetime(*published_struct[:6], tzinfo=timezone.utc)
                    if pub_dt < cutoff:
                        continue
                    pub_str = pub_dt.isoformat()
                else:
                    continue

                duration = entry.get("itunes_duration", "")
                articles.append(
                    {
                        "id": _make_id(
                            entry.get("link", podcast["name"]), entry.get("title", "")
                        ),
                        "title": f"{podcast['name']}: {entry.get('title', 'New Episode')}",
                        "url": entry.get("link", ""),
                        "source": "Podcast",
                        "source_label": podcast["name"],
                        "summary": _strip_html(
                            entry.get("summary", entry.get("description", ""))[:400]
                        ),
                        "published": pub_str,
                        "topic_hint": podcast["topic"],
                        "image_url": None,
                        "is_podcast": True,
                        "podcast_name": podcast["name"],
                        "podcast_duration": duration,
                        "score_override": 80,
                    }
                )
            except Exception as e:
                logger.warning(f"Podcast {podcast['name']} failed: {e}")

        logger.info(f"Podcasts: found {len(articles)} new episodes")
        return articles
