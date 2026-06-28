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


HISTORY_DIR = os.path.join(os.path.dirname(__file__), "..", "feedback")
HISTORY_FILE = os.path.join(HISTORY_DIR, "sent_history.jsonl")


def load_sent_history() -> tuple[set[str], set[str]]:
    """Load the IDs and URLs of articles sent in previous digests."""
    sent_ids: set[str] = set()
    sent_urls: set[str] = set()

    if os.environ.get("DISABLE_HISTORY_FILTER") == "true":
        return sent_ids, sent_urls

    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                for line in f:
                    if line.strip():
                        entry = json.loads(line)
                        if "id" in entry:
                            sent_ids.add(entry["id"])
                        if "url" in entry:
                            sent_urls.add(entry["url"])
        except Exception as e:
            logger.warning(f"Failed to load sent history: {e}")
    return sent_ids, sent_urls


def save_sent_history(articles: list[dict]):
    """Append the sent articles to the history and keep the last 500 entries."""
    import datetime

    existing_entries = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                for line in f:
                    if line.strip():
                        existing_entries.append(json.loads(line))
        except Exception as e:
            logger.warning(f"Failed to read sent history for pruning: {e}")

    now = datetime.datetime.utcnow().isoformat() + "Z"
    for a in articles:
        existing_entries.append({
            "id": a["id"],
            "url": a.get("url", ""),
            "title": a.get("title", ""),
            "timestamp": now
        })

    max_history = 500
    if len(existing_entries) > max_history:
        existing_entries = existing_entries[-max_history:]

    try:
        os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
        with open(HISTORY_FILE, "w") as f:
            for entry in existing_entries:
                f.write(json.dumps(entry) + "\n")
        logger.info(f"Saved {len(articles)} articles to sent history. Total history: {len(existing_entries)}")
    except Exception as e:
        logger.error(f"Failed to write sent history: {e}")


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

    # Deduplicate by ID and filter out historically sent articles
    sent_ids, sent_urls = load_sent_history()
    seen: set[str] = set()
    unique: list[dict] = []
    for a in all_articles:
        a_id = a["id"]
        a_url = a.get("url", "")
        if a_id not in seen and a_id not in sent_ids and a_url not in sent_urls:
            seen.add(a_id)
            unique.append(a)

    logger.info(f"Total unique new articles fetched: {len(unique)}")
    return unique


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    key = os.environ.get("NYT_API_KEY", "")
    articles = fetch_all(key)
    print(json.dumps(articles[:3], indent=2, default=str))
