"""
reddit.py — Reddit JSON source plugin.
Fetches hot/top posts from configured subreddits via the public JSON API.
"""

import json
import logging
import urllib.request
from datetime import datetime, timezone

from .base import BaseSource, SourceFetchError

logger = logging.getLogger(__name__)


def _make_id(url: str, title: str) -> str:
    import hashlib

    return hashlib.sha256(f"{url}|{title}".encode()).hexdigest()[:16]


class Source(BaseSource):
    name = "reddit"

    def fetch(self) -> list[dict]:
        subreddits = self.config.get("subreddits", {})
        sort = self.config.get("sort", "hot")
        limit = self.config.get("limit", 10)
        min_score = self.config.get("min_score", 100)
        headers = {"User-Agent": "daily-news-digest/1.0 (personal project)"}

        articles = []

        for topic, subs in subreddits.items():
            for sub in subs:
                url = f"https://www.reddit.com/r/{sub}/{sort}.json?limit={limit}"
                try:
                    req = urllib.request.Request(url, headers=headers)
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        data = json.loads(resp.read())

                    for post in data.get("data", {}).get("children", []):
                        d = post.get("data", {})
                        if d.get("score", 0) < min_score:
                            continue
                        if d.get("is_self") and not d.get("selftext"):
                            continue
                        link = d.get("url", "")
                        if not link:
                            continue
                        thumbnail = d.get("thumbnail", "")
                        articles.append(
                            {
                                "id": _make_id(link, d.get("title", "")),
                                "title": d.get("title", ""),
                                "url": link,
                                "reddit_url": f"https://reddit.com{d.get('permalink', '')}",
                                "source": "Reddit",
                                "source_label": f"r/{sub}",
                                "summary": (d.get("selftext", "") or "")[:500],
                                "published": datetime.fromtimestamp(
                                    d.get("created_utc", 0), tz=timezone.utc
                                ).isoformat(),
                                "topic_hint": topic,
                                "image_url": (
                                    thumbnail if thumbnail.startswith("http") else None
                                ),
                                "reddit_score": d.get("score", 0),
                                "num_comments": d.get("num_comments", 0),
                            }
                        )
                except Exception as e:
                    logger.warning(f"Reddit r/{sub} failed: {e}")

        logger.info(f"Reddit: fetched {len(articles)} posts")
        return articles
