"""
fetch.py — Thin wrapper that loads source plugins and returns combined articles.
Source logic lives in src/sources/<plugin>.py.
"""

import json
import logging
import os

import yaml

from sources import load_sources
from sources.base import SourceFetchError

logger = logging.getLogger(__name__)

CONFIG_DIR = os.path.join(os.path.dirname(__file__), "..", "config")


def load_config(filename: str) -> dict:
    with open(os.path.join(CONFIG_DIR, filename)) as f:
        return yaml.safe_load(f)


def fetch_all(nyt_api_key: str) -> list[dict]:
    """Load all enabled source plugins and return combined, deduplicated articles."""
    config = load_config("sources.yaml")
    sources_config = config.get("sources", [])

    plugins = load_sources(sources_config)

    all_articles: list[dict] = []
    for plugin in plugins:
        try:
            articles = plugin.fetch()
            all_articles.extend(articles)
        except SourceFetchError as e:
            logger.warning(f"Source '{plugin.name}' failed: {e} — skipping")
        except Exception as e:
            logger.warning(
                f"Source '{plugin.name}' raised unexpected error: {e} — skipping"
            )

    # Deduplicate by ID
    seen: set[str] = set()
    unique: list[dict] = []
    for a in all_articles:
        if a["id"] not in seen:
            seen.add(a["id"])
            unique.append(a)

    logger.info(f"Total unique articles fetched: {len(unique)}")
    return unique


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    key = os.environ.get("NYT_API_KEY", "")
    articles = fetch_all(key)
    print(json.dumps(articles[:3], indent=2, default=str))
