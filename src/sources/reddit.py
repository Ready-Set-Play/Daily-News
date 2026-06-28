"""
reddit.py — Reddit source plugin.
Fetches hot/top posts via the OAuth client_credentials flow.
"""

import base64
import json
import logging
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from .base import BaseSource

logger = logging.getLogger(__name__)

_TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
_API_BASE = "https://oauth.reddit.com"


def _make_id(url: str, title: str) -> str:
    import hashlib

    return hashlib.sha256(f"{url}|{title}".encode()).hexdigest()[:16]


def _get_token(client_id: str, client_secret: str) -> str:
    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    body = urllib.parse.urlencode({"grant_type": "client_credentials"}).encode()
    req = urllib.request.Request(
        _TOKEN_URL,
        data=body,
        headers={
            "Authorization": f"Basic {credentials}",
            "User-Agent": "daily-news-digest/1.0 (personal project)",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read())
    return data["access_token"]


class Source(BaseSource):
    name = "reddit"
    requires_auth = True

    def is_configured(self) -> bool:
        import os
        client_id_env = self.auth.get("client_id_env", "REDDIT_CLIENT_ID")
        client_secret_env = self.auth.get("client_secret_env", "REDDIT_CLIENT_SECRET")
        return bool(os.environ.get(client_id_env, "")) and bool(os.environ.get(client_secret_env, ""))

    def fetch(self) -> list[dict]:
        import os

        client_id = os.environ.get(
            self.auth.get("client_id_env", "REDDIT_CLIENT_ID"), ""
        )
        client_secret = os.environ.get(
            self.auth.get("client_secret_env", "REDDIT_CLIENT_SECRET"), ""
        )

        if not client_id or not client_secret:
            logger.warning("Reddit: missing REDDIT_CLIENT_ID or REDDIT_CLIENT_SECRET — skipping")
            return []

        subreddits = self.config.get("subreddits", {})
        sort = self.config.get("sort", "hot")
        limit = self.config.get("limit", 10)
        min_score = self.config.get("min_score", 100)

        try:
            token = _get_token(client_id, client_secret)
        except Exception as e:
            logger.warning(f"Reddit: OAuth token fetch failed: {e}")
            return []

        headers = {
            "Authorization": f"Bearer {token}",
            "User-Agent": "daily-news-digest/1.0 (personal project)",
        }

        articles = []

        for topic, subs in subreddits.items():
            for sub in subs:
                url = f"{_API_BASE}/r/{sub}/{sort}.json?limit={limit}"
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
