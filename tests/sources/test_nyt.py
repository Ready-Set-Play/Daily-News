"""
tests/sources/test_nyt.py — Unit tests for the NYT source plugin.
Uses VCR cassettes for HTTP — no live network calls.

Record cassettes once with real credentials:
  pytest tests/sources/test_nyt.py --record-mode=once

Subsequent runs (and CI) replay from cassette:
  pytest tests/sources/test_nyt.py
"""

import pytest

pytest.importorskip("vcr")

import vcr

from sources.nyt import Source

CASSETTE = "tests/sources/cassettes/test_nyt_fetch.yaml"

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

NYT_CONFIG = {
    "base_url": "https://api.nytimes.com/svc",
    "sections": ["technology"],
    "most_popular_days": 7,
}
NYT_AUTH = {"api_key_env": "NYT_API_KEY"}


@vcr.use_cassette(
    CASSETTE,
    record_mode="new_episodes",
    allow_playback_repeats=True,
    filter_query_parameters=["api-key"],
)
def test_nyt_returns_articles():
    plugin = Source(NYT_CONFIG, NYT_AUTH)
    articles = plugin.fetch()
    assert len(articles) > 0, "Expected at least one NYT article"


@vcr.use_cassette(
    CASSETTE,
    record_mode="new_episodes",
    allow_playback_repeats=True,
    filter_query_parameters=["api-key"],
)
def test_nyt_required_fields():
    plugin = Source(NYT_CONFIG, NYT_AUTH)
    articles = plugin.fetch()
    for article in articles:
        for field in REQUIRED_FIELDS:
            assert (
                field in article
            ), f"Missing field '{field}' in NYT article: {article.get('title')}"


@vcr.use_cassette(
    CASSETTE,
    record_mode="new_episodes",
    allow_playback_repeats=True,
    filter_query_parameters=["api-key"],
)
def test_nyt_is_nyt_flag():
    plugin = Source(NYT_CONFIG, NYT_AUTH)
    articles = plugin.fetch()
    for article in articles:
        assert (
            article.get("is_nyt") is True
        ), f"Missing is_nyt=True on: {article.get('title')}"


@vcr.use_cassette(
    CASSETTE,
    record_mode="new_episodes",
    allow_playback_repeats=True,
    filter_query_parameters=["api-key"],
)
def test_nyt_source_field():
    plugin = Source(NYT_CONFIG, NYT_AUTH)
    articles = plugin.fetch()
    for article in articles:
        assert article["source"] == "NYT"


def test_nyt_is_configured_without_key(monkeypatch):
    monkeypatch.delenv("NYT_API_KEY", raising=False)
    plugin = Source(NYT_CONFIG, NYT_AUTH)
    assert plugin.is_configured() is False


def test_nyt_is_configured_with_key(monkeypatch):
    monkeypatch.setenv("NYT_API_KEY", "test-key")
    plugin = Source(NYT_CONFIG, NYT_AUTH)
    assert plugin.is_configured() is True
