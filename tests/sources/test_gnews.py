"""
tests/sources/test_gnews.py — Unit tests for the GNews source plugin.
Uses VCR cassettes for HTTP — no live network calls.

Record:  GNEWS_API_KEY=<key> pytest tests/sources/test_gnews.py --record-mode=once
Replay:  pytest tests/sources/test_gnews.py
"""

import pytest

pytest.importorskip("vcr")

import vcr

from sources.gnews import Source

CASSETTE = "tests/sources/cassettes/test_gnews_fetch.yaml"

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

GNEWS_CONFIG = {
    "queries": {"ai_coding": ["Claude Anthropic"]},
    "max_per_query": 10,
    "lang": "en",
    "country": "us",
}
GNEWS_AUTH = {"api_key_env": "GNEWS_API_KEY"}


@vcr.use_cassette(CASSETTE, record_mode="new_episodes", allow_playback_repeats=True,
                  filter_query_parameters=["apikey"])
def test_gnews_returns_articles(mock_env):
    plugin = Source(GNEWS_CONFIG, GNEWS_AUTH)
    articles = plugin.fetch()
    assert len(articles) > 0


@vcr.use_cassette(CASSETTE, record_mode="new_episodes", allow_playback_repeats=True,
                  filter_query_parameters=["apikey"])
def test_gnews_required_fields(mock_env):
    plugin = Source(GNEWS_CONFIG, GNEWS_AUTH)
    articles = plugin.fetch()
    for article in articles:
        for field in REQUIRED_FIELDS:
            assert field in article, f"Missing field '{field}' in article: {article.get('title')}"


@vcr.use_cassette(CASSETTE, record_mode="new_episodes", allow_playback_repeats=True,
                  filter_query_parameters=["apikey"])
def test_gnews_source_field(mock_env):
    plugin = Source(GNEWS_CONFIG, GNEWS_AUTH)
    articles = plugin.fetch()
    for article in articles:
        assert article["source"] == "GNews"


@vcr.use_cassette(CASSETTE, record_mode="new_episodes", allow_playback_repeats=True,
                  filter_query_parameters=["apikey"])
def test_gnews_real_urls(mock_env):
    plugin = Source(GNEWS_CONFIG, GNEWS_AUTH)
    articles = plugin.fetch()
    for article in articles:
        assert "news.google.com" not in article["url"], (
            f"GNews returned a Google redirect URL instead of a real URL: {article['url']}"
        )


@vcr.use_cassette(CASSETTE, record_mode="new_episodes", allow_playback_repeats=True,
                  filter_query_parameters=["apikey"])
def test_gnews_topic_hint_set(mock_env):
    plugin = Source(GNEWS_CONFIG, GNEWS_AUTH)
    articles = plugin.fetch()
    for article in articles:
        assert article["topic_hint"] == "ai_coding"


def test_gnews_is_configured_without_key(monkeypatch):
    monkeypatch.delenv("GNEWS_API_KEY", raising=False)
    plugin = Source(GNEWS_CONFIG, GNEWS_AUTH)
    assert plugin.is_configured() is False


def test_gnews_is_configured_with_key(monkeypatch):
    monkeypatch.setenv("GNEWS_API_KEY", "test-key")
    plugin = Source(GNEWS_CONFIG, GNEWS_AUTH)
    assert plugin.is_configured() is True
