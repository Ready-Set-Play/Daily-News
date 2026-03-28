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
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
        }

        articles = []

        import feedparser

        for topic, subs in subreddits.items():
            for sub in subs:
                url = f"https://www.reddit.com/r/{sub}/{sort}.rss?limit={limit}"
                try:
                    req = urllib.request.Request(url, headers=headers)
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        raw_xml = resp.read()
                    
                    feed = feedparser.parse(raw_xml)

                    for entry in feed.entries:
                        link = entry.get("link", "")
                        if not link:
                            continue
                        
                        summary_html = entry.get("summary", "")
                        
                        articles.append(
                            {
                                "id": _make_id(link, entry.get("title", "")),
                                "title": entry.get("title", ""),
                                "url": link,
                                "reddit_url": link,  # RSS link is the reddit permalink
                                "source": "Reddit",
                                "source_label": f"r/{sub}",
                                "summary": summary_html[:500],  # HTML snippet
                                "published": entry.get("published", ""),
                                "topic_hint": topic,
                                "image_url": None, # Complex to extract from RSS HTML reliably
                                "reddit_score": 0, # Not provided in RSS
                                "num_comments": 0, # Not provided in RSS
                            }
                        )
                except Exception as e:
                    logger.warning(f"Reddit r/{sub} failed: {e}")

        logger.info(f"Reddit: fetched {len(articles)} posts")
        return articles
