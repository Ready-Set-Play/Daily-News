"""
google_news.py — Google News RSS source plugin.
Fetches articles via Google News RSS search queries.
"""

import logging
import urllib.parse

import feedparser

from .base import BaseSource, SourceFetchError

logger = logging.getLogger(__name__)


def _make_id(url: str, title: str) -> str:
    import hashlib

    return hashlib.sha256(f"{url}|{title}".encode()).hexdigest()[:16]


def _clean_url(url: str) -> str:
    """Google News wraps URLs — return as-is; redirect works for users."""
    return url


class Source(BaseSource):
    name = "google_news"

    def fetch(self) -> list[dict]:
        queries = self.config.get("queries", {})
        articles = []

        for topic, query_list in queries.items():
            for query in query_list:
                encoded = urllib.parse.quote(query)
                url = f"https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en"
                try:
                    feed = feedparser.parse(url)
                    for entry in feed.entries[:5]:
                        link = _clean_url(entry.get("link", ""))
                        if not link:
                            continue
                        articles.append(
                            {
                                "id": _make_id(link, entry.get("title", "")),
                                "title": entry.get("title", ""),
                                "url": link,
                                "source": "Google News",
                                "source_label": entry.get("source", {}).get(
                                    "title", "Google News"
                                ),
                                "summary": entry.get("summary", ""),
                                "published": entry.get("published", ""),
                                "topic_hint": topic,
                                "image_url": None,
                            }
                        )
                except Exception as e:
                    logger.warning(f"Google News query '{query}' failed: {e}")

        logger.info(f"Google News: fetched {len(articles)} articles")
        return articles
