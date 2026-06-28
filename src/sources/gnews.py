"""
gnews.py — GNews.io source plugin.
Fetches articles via the GNews API (https://gnews.io).
Free tier: 100 requests/day, max 10 articles per request.
Requires GNEWS_API_KEY environment variable.
Get a key at https://gnews.io.
"""

import json
import logging
import os
import urllib.parse
import urllib.request

from .base import BaseSource

logger = logging.getLogger(__name__)


def _make_id(url: str, title: str) -> str:
    import hashlib

    return hashlib.sha256(f"{url}|{title}".encode()).hexdigest()[:16]


class Source(BaseSource):
    name = "gnews"
    requires_auth = True

    def fetch(self) -> list[dict]:
        env_var = self.auth.get("api_key_env", "GNEWS_API_KEY")
        api_key = os.environ.get(env_var, "")
        queries = self.config.get("queries", {})
        max_per_query = self.config.get("max_per_query", 10)
        lang = self.config.get("lang", "en")
        country = self.config.get("country", "us")

        articles = []

        for topic, query_list in queries.items():
            for query in query_list:
                params = urllib.parse.urlencode({
                    "q": query,
                    "lang": lang,
                    "country": country,
                    "max": max_per_query,
                    "apikey": api_key,
                })
                url = f"https://gnews.io/api/v4/search?{params}"
                try:
                    req = urllib.request.Request(url, headers={
                        "User-Agent": "daily-news-digest/1.0",
                        "Accept": "application/json",
                    })
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        data = json.loads(resp.read())

                    for item in data.get("articles", []):
                        article_url = item.get("url", "")
                        if not article_url:
                            continue
                        text = item.get("description") or item.get("content") or ""
                        articles.append({
                            "id": _make_id(article_url, item.get("title", "")),
                            "title": item.get("title", ""),
                            "url": article_url,
                            "source": "GNews",
                            "source_label": item.get("source", {}).get("name", "GNews"),
                            "summary": text[:300],
                            "published": item.get("publishedAt", ""),
                            "topic_hint": topic,
                            "image_url": item.get("image"),
                        })
                except Exception as e:
                    logger.warning(f"GNews query '{query}' failed: {e}")

        logger.info(f"GNews: fetched {len(articles)} articles")
        return articles
