"""
tests/sources/test_google_news.py — Unit tests for the Google News source plugin.
Uses VCR cassettes for HTTP — no live network calls.

Record:  pytest tests/sources/test_google_news.py --record-mode=once
Replay:  pytest tests/sources/test_google_news.py
"""

import pytest

pytest.importorskip("vcr")

import vcr

from sources.google_news import Source

CASSETTE = "tests/sources/cassettes/test_google_news_fetch.yaml"

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

GN_CONFIG = {
    "queries": {
        "ai_coding": ["Claude Anthropic"],
    }
}


@vcr.use_cassette(CASSETTE, record_mode="new_episodes", allow_playback_repeats=True)
def test_google_news_returns_articles():
    plugin = Source(GN_CONFIG, {})
    articles = plugin.fetch()
    assert len(articles) > 0


@vcr.use_cassette(CASSETTE, record_mode="new_episodes", allow_playback_repeats=True)
def test_google_news_required_fields():
    plugin = Source(GN_CONFIG, {})
    articles = plugin.fetch()
    for article in articles:
        for field in REQUIRED_FIELDS:
            assert (
                field in article
            ), f"Missing field '{field}' in article: {article.get('title')}"


@vcr.use_cassette(CASSETTE, record_mode="new_episodes", allow_playback_repeats=True)
def test_google_news_source_field():
    plugin = Source(GN_CONFIG, {})
    articles = plugin.fetch()
    for article in articles:
        assert article["source"] == "Google News"


@vcr.use_cassette(CASSETTE, record_mode="new_episodes", allow_playback_repeats=True)
def test_google_news_topic_hint_set():
    plugin = Source(GN_CONFIG, {})
    articles = plugin.fetch()
    for article in articles:
        assert article["topic_hint"] == "ai_coding"
