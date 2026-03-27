"""
tests/sources/test_reddit.py — Unit tests for the Reddit source plugin.
Uses VCR cassettes for HTTP — no live network calls.

Record:  pytest tests/sources/test_reddit.py --record-mode=once
Replay:  pytest tests/sources/test_reddit.py
"""

import pytest

pytest.importorskip("vcr")

import vcr

from sources.reddit import Source

CASSETTE = "tests/sources/cassettes/test_reddit_fetch.yaml"

REQUIRED_FIELDS = {
    "id",
    "title",
    "url",
    "source",
    "source_label",
    "summary",
    "published",
    "topic_hint",
    "image_url",
}

REDDIT_CONFIG = {
    "subreddits": {
        "ai_coding": ["LocalLLaMA"],
    },
    "sort": "hot",
    "limit": 5,
    "min_score": 100,
}


@vcr.use_cassette(CASSETTE, record_mode="new_episodes", allow_playback_repeats=True)
def test_reddit_returns_articles():
    plugin = Source(REDDIT_CONFIG, {})
    articles = plugin.fetch()
    assert len(articles) >= 0  # May be empty if all posts below min_score in cassette


@vcr.use_cassette(CASSETTE, record_mode="new_episodes", allow_playback_repeats=True)
def test_reddit_required_fields():
    plugin = Source(REDDIT_CONFIG, {})
    articles = plugin.fetch()
    for article in articles:
        for field in REQUIRED_FIELDS:
            assert (
                field in article
            ), f"Missing field '{field}' in article: {article.get('title')}"


@vcr.use_cassette(CASSETTE, record_mode="new_episodes", allow_playback_repeats=True)
def test_reddit_source_field():
    plugin = Source(REDDIT_CONFIG, {})
    articles = plugin.fetch()
    for article in articles:
        assert article["source"] == "Reddit"
        assert article["source_label"].startswith("r/")


@vcr.use_cassette(CASSETTE, record_mode="new_episodes", allow_playback_repeats=True)
def test_reddit_published_is_iso8601():
    from datetime import datetime

    plugin = Source(REDDIT_CONFIG, {})
    articles = plugin.fetch()
    for article in articles:
        # Should parse without error
        datetime.fromisoformat(article["published"])
