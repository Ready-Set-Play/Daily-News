"""
conftest.py — Shared pytest fixtures for the daily-brief test suite.

Three stub layers (per FR-006):
  1. HTTP:     VCR cassettes (per-plugin test files)
  2. LLM:      mock_anthropic fixture — zero API calls, zero cost
  3. Resend:   mock_resend fixture — no emails sent
"""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Environment stubs
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_env(monkeypatch):
    """Set dummy credentials so the pipeline doesn't abort on missing env vars."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")
    monkeypatch.setenv("RESEND_API_KEY", "test-resend-key")
    monkeypatch.setenv("RECIPIENT_EMAIL", "test@example.com")
    monkeypatch.setenv("NYT_API_KEY", "test-nyt-key")
    monkeypatch.setenv("GNEWS_API_KEY", "test-gnews-key")
    monkeypatch.setenv("REDDIT_CLIENT_ID", "test-reddit-id")
    monkeypatch.setenv("REDDIT_CLIENT_SECRET", "test-reddit-secret")
    monkeypatch.setenv("FROM_EMAIL", "Daily Brief <digest@example.com>")
    monkeypatch.setenv("FEEDBACK_BASE_URL", "https://feedback.example.com")
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("DISABLE_HISTORY_FILTER", "true")
    # FEEDBACK_BASE_URL is a module-level constant in summarize — patch it directly
    try:
        import summarize
        monkeypatch.setattr(summarize, "FEEDBACK_BASE_URL", "https://feedback.example.com")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# LLM stub — returns deterministic canned responses, zero API cost
# The mock patches load_llm_client() to return a fake LLMClient whose
# complete() method inspects the prompt and returns canned JSON.
# ---------------------------------------------------------------------------


def _make_llm_mock():
    """Build a mock LLMClient with canned score + summary responses."""

    def fake_complete(prompt: str, max_tokens: int = 2000) -> str:
        # Deduplication call: return empty groups (no merges)
        if "deduplication" in prompt.lower() or "same story" in prompt.lower():
            return "[]"

        # Scoring call: assign score=75, topic=technology to every article
        if (
            "score" in prompt.lower()
            and "idx" in prompt.lower()
            and "topic" in prompt.lower()
        ):
            try:
                start = prompt.find("[{")
                end = prompt.rfind("}]") + 2
                items = json.loads(prompt[start:end])
                scores = [
                    {"idx": it["idx"], "score": 75, "topic": "technology"}
                    for it in items
                ]
                return json.dumps(scores)
            except Exception:
                return '[{"idx": 0, "score": 75, "topic": "technology"}]'

        # Summarization call: return a canned summary per article
        if "summary" in prompt.lower() and "idx" in prompt.lower():
            try:
                start = prompt.find("[{")
                end = prompt.rfind("}]") + 2
                items = json.loads(prompt[start:end])
                summaries = [
                    {"idx": it["idx"], "summary": "Test summary for this article."}
                    for it in items
                ]
                return json.dumps(summaries)
            except Exception:
                return '[{"idx": 0, "summary": "Test summary for this article."}]'

        return "[]"

    mock_client = MagicMock()
    mock_client.name = "anthropic"
    mock_client.complete.side_effect = fake_complete
    return mock_client


@pytest.fixture
def mock_anthropic(monkeypatch):
    """Replace load_llm_client() with a fake that returns canned JSON.
    Score: assigns score=75, topic='technology' to every article.
    Summary: returns 'Test summary for this article.' for every article.
    Zero API calls, zero cost."""
    mock_client = _make_llm_mock()
    monkeypatch.setattr("llm.load_llm_client", lambda: mock_client)
    # Patch in score and summarize modules if already imported
    try:
        import score

        monkeypatch.setattr("score.load_llm_client", lambda: mock_client)
    except Exception:
        pass
    try:
        import summarize

        monkeypatch.setattr("summarize.load_llm_client", lambda: mock_client)
    except Exception:
        pass
    return mock_client


# ---------------------------------------------------------------------------
# Resend stub — no emails sent during tests
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_resend(monkeypatch):
    """Patch resend.Emails.send to return {"id": "test-id"}.
    No emails sent during tests."""
    import resend

    def fake_send(params):
        return {"id": "test-email-id"}

    monkeypatch.setattr(resend.Emails, "send", staticmethod(fake_send))
    return fake_send


# ---------------------------------------------------------------------------
# Sample articles fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_articles():
    """Load the 20 realistic article dicts used in pipeline tests."""
    with open(FIXTURES_DIR / "sample_articles.json") as f:
        return json.load(f)
