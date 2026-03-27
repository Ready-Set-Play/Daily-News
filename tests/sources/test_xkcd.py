"""
tests/sources/test_xkcd.py — Unit tests for the XKCD source plugin.
Uses VCR cassette for HTTP — no live network calls.

Record:  pytest tests/sources/test_xkcd.py --record-mode=once
Replay:  pytest tests/sources/test_xkcd.py
"""

import pytest

pytest.importorskip("vcr")

import vcr

from sources.xkcd import Source

CASSETTE = "tests/sources/cassettes/test_xkcd_fetch.yaml"

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


@vcr.use_cassette(CASSETTE, record_mode="new_episodes", allow_playback_repeats=True)
def test_xkcd_returns_one_article():
    plugin = Source({}, {})
    articles = plugin.fetch()
    assert len(articles) == 1


@vcr.use_cassette(CASSETTE, record_mode="new_episodes", allow_playback_repeats=True)
def test_xkcd_required_fields():
    plugin = Source({}, {})
    articles = plugin.fetch()
    article = articles[0]
    for field in REQUIRED_FIELDS:
        assert field in article, f"Missing field '{field}' in XKCD article"


@vcr.use_cassette(CASSETTE, record_mode="new_episodes", allow_playback_repeats=True)
def test_xkcd_score_override():
    plugin = Source({}, {})
    articles = plugin.fetch()
    assert articles[0]["score_override"] == 95


@vcr.use_cassette(CASSETTE, record_mode="new_episodes", allow_playback_repeats=True)
def test_xkcd_is_xkcd_flag():
    plugin = Source({}, {})
    articles = plugin.fetch()
    assert articles[0]["is_xkcd"] is True


@vcr.use_cassette(CASSETTE, record_mode="new_episodes", allow_playback_repeats=True)
def test_xkcd_source_field():
    plugin = Source({}, {})
    articles = plugin.fetch()
    assert articles[0]["source"] == "XKCD"
    assert articles[0]["source_label"] == "XKCD"
