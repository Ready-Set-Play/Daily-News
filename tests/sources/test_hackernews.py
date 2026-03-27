"""
tests/sources/test_hackernews.py — Unit tests for the Hacker News source plugin.
Uses VCR cassette for HTTP — no live network calls.

Record:  pytest tests/sources/test_hackernews.py --record-mode=once
Replay:  pytest tests/sources/test_hackernews.py
"""

import pytest

pytest.importorskip("vcr")

import vcr

from sources.hackernews import Source

CASSETTE = "tests/sources/cassettes/test_hackernews_fetch.yaml"

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

HN_CONFIG = {
    "min_score": 100,  # Lower threshold for cassette to have results
    "limit": 10,
}


@vcr.use_cassette(CASSETTE, record_mode="new_episodes", allow_playback_repeats=True)
def test_hackernews_returns_articles():
    plugin = Source(HN_CONFIG, {})
    articles = plugin.fetch()
    assert len(articles) > 0


@vcr.use_cassette(CASSETTE, record_mode="new_episodes", allow_playback_repeats=True)
def test_hackernews_required_fields():
    plugin = Source(HN_CONFIG, {})
    articles = plugin.fetch()
    for article in articles:
        for field in REQUIRED_FIELDS:
            assert (
                field in article
            ), f"Missing field '{field}' in HN article: {article.get('title')}"


@vcr.use_cassette(CASSETTE, record_mode="new_episodes", allow_playback_repeats=True)
def test_hackernews_source_field():
    plugin = Source(HN_CONFIG, {})
    articles = plugin.fetch()
    for article in articles:
        assert article["source"] == "Hacker News"
        assert article["source_label"] == "Hacker News"


@vcr.use_cassette(CASSETTE, record_mode="new_episodes", allow_playback_repeats=True)
def test_hackernews_min_score_filter():
    plugin = Source({"min_score": 999999, "limit": 10}, {})
    articles = plugin.fetch()
    # With an impossibly high min_score, no articles should pass the filter
    for article in articles:
        assert article.get("hn_score", 0) >= 999999


def test_hackernews_no_auth_required():
    plugin = Source(HN_CONFIG, {})
    assert plugin.is_configured() is True
