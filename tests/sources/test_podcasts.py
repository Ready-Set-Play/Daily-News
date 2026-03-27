"""
tests/sources/test_podcasts.py — Unit tests for the Podcasts source plugin.
Uses VCR cassette for HTTP — no live network calls.

Record:  pytest tests/sources/test_podcasts.py --record-mode=once
Replay:  pytest tests/sources/test_podcasts.py
"""

import pytest

pytest.importorskip("vcr")

import vcr

from sources.podcasts import Source

CASSETTE = "tests/sources/cassettes/test_podcasts_fetch.yaml"

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

# Use one real feed for cassette recording; a short max_age so cassette captures
# the recency check path
PODCASTS_CONFIG = {
    "feeds": [
        {
            "name": "Acquired",
            "url": "https://feeds.simplecast.com/tti9gUEk",
            "topic": "technology",
        }
    ],
    "max_age_hours": 8760,  # 1 year — ensures cassette replay includes articles
}


@vcr.use_cassette(CASSETTE, record_mode="new_episodes", allow_playback_repeats=True)
def test_podcasts_required_fields():
    plugin = Source(PODCASTS_CONFIG, {})
    articles = plugin.fetch()
    for article in articles:
        for field in REQUIRED_FIELDS:
            assert field in article, f"Missing field '{field}' in podcast article"


@vcr.use_cassette(CASSETTE, record_mode="new_episodes", allow_playback_repeats=True)
def test_podcasts_is_podcast_flag():
    plugin = Source(PODCASTS_CONFIG, {})
    articles = plugin.fetch()
    for article in articles:
        assert article.get("is_podcast") is True


@vcr.use_cassette(CASSETTE, record_mode="new_episodes", allow_playback_repeats=True)
def test_podcasts_score_override():
    plugin = Source(PODCASTS_CONFIG, {})
    articles = plugin.fetch()
    for article in articles:
        assert article["score_override"] == 80


@vcr.use_cassette(CASSETTE, record_mode="new_episodes", allow_playback_repeats=True)
def test_podcasts_source_field():
    plugin = Source(PODCASTS_CONFIG, {})
    articles = plugin.fetch()
    for article in articles:
        assert article["source"] == "Podcast"
