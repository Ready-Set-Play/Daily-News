import os
import json
import pytest
from unittest.mock import patch
from fetch import load_sent_history, save_sent_history, fetch_all


@pytest.fixture
def temp_history_file(tmp_path, monkeypatch):
    # Set the history file path to a temp directory
    temp_file = tmp_path / "sent_history.jsonl"
    monkeypatch.setattr("fetch.HISTORY_FILE", str(temp_file))
    return temp_file


def test_save_and_load_history(temp_history_file, monkeypatch):
    # Ensure it's not disabled
    monkeypatch.delenv("DISABLE_HISTORY_FILTER", raising=False)

    articles = [
        {"id": "art-1", "url": "https://example.com/1", "title": "Article One"},
        {"id": "art-2", "url": "https://example.com/2", "title": "Article Two"},
    ]

    save_sent_history(articles)

    assert temp_history_file.exists()

    sent_ids, sent_urls = load_sent_history()
    assert "art-1" in sent_ids
    assert "art-2" in sent_ids
    assert "https://example.com/1" in sent_urls
    assert "https://example.com/2" in sent_urls


def test_history_pruning(temp_history_file, monkeypatch):
    monkeypatch.delenv("DISABLE_HISTORY_FILTER", raising=False)

    # Save 600 articles (limit is 500)
    articles = [
        {"id": f"art-{i}", "url": f"https://example.com/{i}", "title": f"Title {i}"}
        for i in range(600)
    ]
    save_sent_history(articles)

    sent_ids, _ = load_sent_history()
    # It should prune to the last 500
    assert len(sent_ids) == 500
    # First 100 should be pruned
    assert "art-0" not in sent_ids
    assert "art-99" not in sent_ids
    # Last ones should be present
    assert "art-100" in sent_ids
    assert "art-599" in sent_ids


def test_fetch_all_filters_duplicates(temp_history_file, monkeypatch):
    monkeypatch.delenv("DISABLE_HISTORY_FILTER", raising=False)
    monkeypatch.setenv("NYT_API_KEY", "dummy")

    # Mock load_config and load_sources to return dummy sources/configs
    with patch("fetch.load_config") as mock_load_config, \
         patch("fetch.load_sources") as mock_load_sources:

        mock_load_config.return_value = {"sources": [{"plugin": "dummy"}]}

        from sources.base import BaseSource

        class DummySource(BaseSource):
            name = "dummy"
            def fetch(self):
                return [
                    {"id": "art-1", "url": "https://example.com/1", "title": "Article One"},
                    {"id": "art-2", "url": "https://example.com/2", "title": "Article Two"},
                    {"id": "art-3", "url": "https://example.com/3", "title": "Article Three"},
                ]

        mock_load_sources.return_value = [DummySource({}, {})]

        # Seed sent history with art-1
        save_sent_history([{"id": "art-1", "url": "https://example.com/1", "title": "Article One"}])

        # Fetch articles
        unique = fetch_all("dummy_key")

        # It should filter out art-1, leaving art-2 and art-3
        assert len(unique) == 2
        fetched_ids = {a["id"] for a in unique}
        assert "art-1" not in fetched_ids
        assert "art-2" in fetched_ids
        assert "art-3" in fetched_ids
