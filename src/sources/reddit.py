"""
reddit.py — Reddit source plugin.
Fetches hot/top posts via public Redlib instances (without OAuth/authentication).
"""

import json
import logging
import random
import re
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser

from .base import BaseSource

logger = logging.getLogger(__name__)


def _make_id(url: str, title: str) -> str:
    import hashlib

    return hashlib.sha256(f"{url}|{title}".encode()).hexdigest()[:16]


class RedlibParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.posts = []
        self.current_post = None
        self.in_title = False
        self.in_title_text = False
        self.in_score = False
        self.in_body = False
        self.in_created = False
        self.in_comments = False

        self.current_text = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        class_name = attrs_dict.get("class", "")

        # Detect start of a post div
        if tag == "div" and "post" in class_name.split():
            if self.current_post is not None:
                self.posts.append(self.current_post)
            self.current_post = {
                "id": attrs_dict.get("id", ""),
                "subreddit": "",
                "title": "",
                "permalink": "",
                "external_url": "",
                "score": 0,
                "created_time": "",
                "comments_count": 0,
                "selftext": "",
            }

        if self.current_post is None:
            return

        if tag == "a" and "post_subreddit" in class_name:
            self.current_post["subreddit"] = attrs_dict.get("href", "").replace("/r/", "")

        elif tag == "span" and "created" in class_name:
            self.in_created = True
            if "title" in attrs_dict:
                self.current_post["created_time"] = attrs_dict["title"]

        elif tag == "h2" and "post_title" in class_name:
            self.in_title = True

        elif tag == "a" and self.in_title:
            if "post_flair" not in class_name.split():
                self.current_post["permalink"] = attrs_dict.get("href", "")
                self.in_title_text = True

        elif tag == "a" and "post_thumbnail" in class_name:
            self.current_post["external_url"] = attrs_dict.get("href", "")

        elif tag == "div" and "post_score" in class_name:
            self.in_score = True
            self.current_text = []

        elif tag == "div" and "post_body" in class_name:
            self.in_body = True
            self.current_text = []

        elif tag == "a" and "post_comments" in class_name:
            self.in_comments = True
            self.current_text = []

    def handle_endtag(self, tag):
        if self.current_post is None:
            return

        if tag == "h2" and self.in_title:
            self.in_title = False
        elif tag == "a" and self.in_title_text:
            self.in_title_text = False
        elif tag == "span" and self.in_created:
            self.in_created = False
        elif tag == "div" and self.in_score:
            self.in_score = False
            score_str = "".join(self.current_text).strip()
            try:
                score_str = re.sub(r"[^\d]", "", score_str)
                self.current_post["score"] = int(score_str) if score_str else 0
            except ValueError:
                self.current_post["score"] = 0
        elif tag == "div" and self.in_body:
            self.in_body = False
            self.current_post["selftext"] = "".join(self.current_text).strip()
        elif tag == "a" and self.in_comments:
            self.in_comments = False
            comm_str = "".join(self.current_text).strip()
            try:
                comm_str = re.sub(r"[^\d]", "", comm_str)
                self.current_post["comments_count"] = int(comm_str) if comm_str else 0
            except ValueError:
                self.current_post["comments_count"] = 0

    def handle_data(self, data):
        if self.current_post is None:
            return

        if self.in_title_text:
            self.current_post["title"] += data
        elif self.in_score or self.in_body or self.in_comments:
            self.current_text.append(data)

    def close(self):
        super().close()
        if self.current_post:
            self.posts.append(self.current_post)


DEFAULT_INSTANCES = [
    "https://red.artemislena.eu",
    "https://redlib.privacyredirect.com",
    "https://redlib.nadeko.net",
    "https://redlib.privadency.com",
    "https://redlib.catsarch.com",
    "https://redlib.perennialte.ch",
    "https://redlib.r4fo.com",
    "https://redlib.cow.rip",
]


class Source(BaseSource):
    name = "reddit"
    requires_auth = False

    def is_configured(self) -> bool:
        return True

    def fetch(self) -> list[dict]:
        subreddits = self.config.get("subreddits", {})
        sort = self.config.get("sort", "hot")
        limit = self.config.get("limit", 10)
        min_score = self.config.get("min_score", 100)

        instances = self.config.get("instances", DEFAULT_INSTANCES).copy()
        random.shuffle(instances)

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        articles = []

        for topic, subs in subreddits.items():
            for sub in subs:
                success = False
                for instance in instances:
                    base_url = instance.rstrip("/")
                    url = f"{base_url}/r/{sub}/{sort}"
                    try:
                        req = urllib.request.Request(url, headers=headers)
                        with urllib.request.urlopen(req, timeout=10) as resp:
                            html_content = resp.read().decode("utf-8", errors="ignore")

                        parser = RedlibParser()
                        parser.feed(html_content)
                        parser.close()

                        count = 0
                        for p in parser.posts:
                            if limit and count >= limit:
                                break

                            score = p["score"]
                            if score < min_score:
                                continue

                            permalink = "https://www.reddit.com" + p["permalink"]
                            url_field = p["external_url"]
                            if not url_field or url_field.startswith("/"):
                                url_field = permalink

                            published = ""
                            if p["created_time"]:
                                try:
                                    dt = datetime.strptime(
                                        p["created_time"], "%b %d %Y, %H:%M:%S UTC"
                                    ).replace(tzinfo=timezone.utc)
                                    published = dt.isoformat()
                                except Exception:
                                    published = datetime.now(timezone.utc).isoformat()
                            else:
                                published = datetime.now(timezone.utc).isoformat()

                            articles.append(
                                {
                                    "id": _make_id(permalink, p["title"].strip()),
                                    "title": p["title"].strip(),
                                    "url": url_field,
                                    "reddit_url": permalink,
                                    "source": "Reddit",
                                    "source_label": f"r/{sub}",
                                    "summary": p["selftext"][:500],
                                    "published": published,
                                    "topic_hint": topic,
                                    "image_url": None,
                                    "reddit_score": score,
                                    "num_comments": p["comments_count"],
                                }
                            )
                            count += 1

                        success = True
                        break  # Subreddit fetched successfully, exit instance loop
                    except Exception as e:
                        logger.warning(
                            f"Reddit fetch from {instance} for r/{sub} failed: {e}"
                        )
                        continue

                if not success:
                    logger.error(
                        f"Failed to fetch r/{sub} from all configured Redlib instances."
                    )

        logger.info(f"Reddit: fetched {len(articles)} posts")
        return articles
