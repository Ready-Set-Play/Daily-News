"""
test_plugin_contract.py — Parametrized schema validation for all source plugins.

For each enabled plugin, calls fetch() against its VCR cassette and asserts
that every returned dict contains REQUIRED_FIELDS with correct types (FR-009).

To add a new plugin to this test:
  1. Create tests/sources/cassettes/test_<plugin>_fetch.yaml
  2. Add an entry to PLUGIN_CONFIGS below
"""

import importlib
from pathlib import Path

import pytest

pytest.importorskip("vcr")
import vcr

REQUIRED_FIELDS = {
    "id": str,
    "title": str,
    "url": str,
    "source": str,
    "source_label": str,
    "summary": str,
    "published": str,
    "topic_hint": (str, type(None)),
    "image_url": (str, type(None)),
}

CASSETTES_DIR = Path("tests/sources/cassettes")

# Each entry: (plugin_module_name, config, auth, cassette_filename)
PLUGIN_CONFIGS = [
    (
        "nyt",
        {
            "base_url": "https://api.nytimes.com/svc",
            "sections": ["technology"],
            "most_popular_days": 7,
        },
        {"api_key_env": "NYT_API_KEY"},
        "test_nyt_fetch.yaml",
    ),
    (
        "gnews",
        {
            "queries": {"ai_coding": ["Claude Anthropic"]},
            "max_per_query": 10,
            "lang": "en",
            "country": "us",
        },
        {"api_key_env": "GNEWS_API_KEY"},
        "test_gnews_fetch.yaml",
    ),
    (
        "reddit",
        {
            "subreddits": {"ai_coding": ["LocalLLaMA"]},
            "sort": "hot",
            "limit": 5,
            "min_score": 100,
        },
        {},
        "test_reddit_fetch.yaml",
    ),
    (
        "xkcd",
        {},
        {},
        "test_xkcd_fetch.yaml",
    ),
    (
        "podcasts",
        {
            "feeds": [
                {
                    "name": "Acquired",
                    "url": "https://feeds.simplecast.com/tti9gUEk",
                    "topic": "technology",
                }
            ],
            "max_age_hours": 8760,
        },
        {},
        "test_podcasts_fetch.yaml",
    ),
    (
        "hackernews",
        {"min_score": 100, "limit": 10},
        {},
        "test_hackernews_fetch.yaml",
    ),
]

# Only parametrize plugins whose cassette file exists
AVAILABLE = [
    pytest.param(name, cfg, auth, cassette, id=name)
    for name, cfg, auth, cassette in PLUGIN_CONFIGS
    if (CASSETTES_DIR / cassette).exists()
]


@pytest.mark.parametrize("plugin_name,config,auth,cassette", AVAILABLE)
def test_plugin_schema(plugin_name, config, auth, cassette, mock_env):
    """Every plugin must return articles with all required fields and correct types."""
    cassette_path = str(CASSETTES_DIR / cassette)
    module = importlib.import_module(f"sources.{plugin_name}")
    plugin = module.Source(config, auth)

    with vcr.VCR().use_cassette(
        cassette_path,
        record_mode="new_episodes",
        allow_playback_repeats=True,
        filter_query_parameters=["api-key", "apikey"],
    ):
        articles = plugin.fetch()

    for article in articles:
        for field, expected_type in REQUIRED_FIELDS.items():
            assert field in article, (
                f"Plugin '{plugin_name}': article missing required field '{field}'\n"
                f"Article title: {article.get('title', '<no title>')}"
            )
            value = article[field]
            if isinstance(expected_type, tuple):
                assert isinstance(value, expected_type), (
                    f"Plugin '{plugin_name}': field '{field}' has type {type(value).__name__}, "
                    f"expected one of {[t.__name__ for t in expected_type]}"
                )
            else:
                assert isinstance(value, expected_type), (
                    f"Plugin '{plugin_name}': field '{field}' has type {type(value).__name__}, "
                    f"expected {expected_type.__name__}"
                )


@pytest.mark.parametrize("plugin_name,config,auth,cassette", AVAILABLE)
def test_plugin_is_base_source(plugin_name, config, auth, cassette):
    """All plugins must inherit from BaseSource (FR-001)."""
    from sources.base import BaseSource

    module = importlib.import_module(f"sources.{plugin_name}")
    plugin = module.Source(config, auth)
    assert isinstance(
        plugin, BaseSource
    ), f"Plugin '{plugin_name}': Source class does not inherit from BaseSource"
