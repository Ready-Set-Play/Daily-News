"""
xkcd.py — XKCD comic source plugin.
Fetches the latest XKCD comic. Always included (score_override: 95).
"""

import json
import logging
import urllib.request

from .base import BaseSource, SourceFetchError

logger = logging.getLogger(__name__)


class Source(BaseSource):
    name = "xkcd"

    def fetch(self) -> list[dict]:
        try:
            with urllib.request.urlopen(
                "https://xkcd.com/info.0.json", timeout=10
            ) as resp:
                data = json.loads(resp.read())
            return [
                {
                    "id": f"xkcd-{data['num']}",
                    "title": f"XKCD #{data['num']}: {data['title']}",
                    "url": f"https://xkcd.com/{data['num']}/",
                    "source": "XKCD",
                    "source_label": "XKCD",
                    "summary": data.get("alt", ""),
                    "published": f"{data['year']}-{data['month']:0>2}-{data['day']:0>2}",
                    "topic_hint": "culture",
                    "image_url": data.get("img"),
                    "xkcd_num": data["num"],
                    "xkcd_alt": data.get("alt", ""),
                    "is_xkcd": True,
                    "score_override": 95,
                }
            ]
        except Exception as e:
            logger.warning(f"XKCD fetch failed: {e}")
            return []
