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
        headers = {
            "User-Agent": "daily-news-digest/1.0 (personal project)",
        }

        articles = []

        for topic, subs in subreddits.items():
            for sub in subs:
                url = f"https://www.reddit.com/r/{sub}/{sort}.json?limit={limit}"
                try:
                    req = urllib.request.Request(url, headers=headers)
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        data = json.loads(resp.read())

                    for post in data["data"]["children"]:
                        p = post["data"]
                        score = p.get("score", 0)
                        if score < min_score:
                            continue
                        link = p.get("url", "")
                        permalink = "https://www.reddit.com" + p.get("permalink", "")
                        published = datetime.fromtimestamp(
                            p.get("created_utc", 0), tz=timezone.utc
                        ).isoformat()
                        articles.append(
                            {
                                "id": _make_id(permalink, p.get("title", "")),
                                "title": p.get("title", ""),
                                "url": link if link else permalink,
                                "reddit_url": permalink,
                                "source": "Reddit",
                                "source_label": f"r/{sub}",
                                "summary": p.get("selftext", "")[:500],
                                "published": published,
                                "topic_hint": topic,
                                "image_url": None,
                                "reddit_score": score,
                                "num_comments": p.get("num_comments", 0),
                            }
                        )
                except Exception as e:
                    logger.warning(f"Reddit r/{sub} failed: {e}")

        logger.info(f"Reddit: fetched {len(articles)} posts")
        return articles
