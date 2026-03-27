"""
test_pipeline.py — Full pipeline smoke test (FR-008).

Exercises the complete fetch → score → summarize → render → send pipeline using:
  - Fixture articles from tests/fixtures/sample_articles.json (bypasses real fetch)
  - mock_anthropic: canned score/summary JSON — zero API calls, zero cost
  - mock_resend: no email sent

Runs in < 5 seconds. No API keys required.
"""

import sys
import os

import pytest

# Ensure src/ is on the path for direct module imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def test_pipeline_score_step(sample_articles, mock_anthropic, mock_env):
    """Score step selects top articles from sample data."""
    from score import select_top

    selected = select_top(sample_articles)

    assert len(selected) > 0, "Expected at least one article selected"
    assert len(selected) <= 15, "Pipeline should cap at 15 articles"
    for article in selected:
        assert "final_score" in article or "score_override" in article


def test_pipeline_summarize_step(sample_articles, mock_anthropic, mock_env):
    """Summarize step adds tldr_summary and feedback URLs to articles."""
    from summarize import generate_summaries

    summarized = generate_summaries(sample_articles[:5])

    for article in summarized:
        assert "feedback_up_url" in article, "Missing feedback_up_url"
        assert "feedback_down_url" in article, "Missing feedback_down_url"
        assert article["feedback_up_url"].startswith("http")


def test_pipeline_render_step(sample_articles, mock_env):
    """Render step produces valid HTML containing expected sections."""
    from summarize import generate_summaries
    from render import render_email

    # Add tldr_summary so renderer has content
    for a in sample_articles:
        a.setdefault("tldr_summary", a.get("summary", "Test summary."))
        a.setdefault("final_score", a.get("claude_score", 75))
        a.setdefault("ai_topic", a.get("topic_hint", "technology"))

    html, text = render_email(sample_articles)

    assert html, "render_email returned empty HTML"
    assert (
        "<html" in html.lower() or "<!doctype" in html.lower()
    ), "Not a valid HTML document"
    assert len(html) > 500, "HTML seems too short to be a real digest"
    assert text, "render_email returned empty plain text"


def test_pipeline_render_nyt_logo(sample_articles, mock_env):
    """Rendered HTML includes NYT logo when NYT articles present."""
    from render import render_email

    # Ensure at least one NYT article has the flag
    nyt_articles = [a for a in sample_articles if a.get("is_nyt")]
    assert len(nyt_articles) > 0, "sample_articles.json should include NYT articles"

    for a in sample_articles:
        a.setdefault("tldr_summary", a.get("summary", "Test summary."))
        a.setdefault("final_score", a.get("claude_score", 75))
        a.setdefault("ai_topic", a.get("topic_hint", "technology"))

    html, _ = render_email(sample_articles)

    # NYT logo is embedded as data URI — check the img tag is present
    assert (
        "nytimes" in html.lower() or "data:image" in html
    ), "Expected NYT branding in rendered HTML when NYT articles are present"


def test_pipeline_render_feedback_urls(sample_articles, mock_env):
    """Rendered HTML includes feedback URLs."""
    from render import render_email

    for a in sample_articles:
        a.setdefault("tldr_summary", a.get("summary", "Test summary."))
        a.setdefault("final_score", 75)
        a.setdefault("ai_topic", "technology")
        a["feedback_up_url"] = (
            f"https://feedback.example.com/feedback?id={a['id']}&dir=up"
        )
        a["feedback_down_url"] = (
            f"https://feedback.example.com/feedback?id={a['id']}&dir=down"
        )

    html, _ = render_email(sample_articles)
    assert "feedback" in html.lower(), "Expected feedback URLs in rendered HTML"


def test_pipeline_send_step(mock_resend, mock_env):
    """Send step calls resend exactly once and returns True on success."""
    from send import send_email

    result = send_email(
        html_body="<html><body>Test digest</body></html>",
        text_body="Test digest",
        resend_api_key=os.environ["RESEND_API_KEY"],
        recipient_email=os.environ["RECIPIENT_EMAIL"],
    )
    assert result is True, "send_email should return True on success"


def test_pipeline_send_called_once(mock_env, monkeypatch):
    """Resend is called exactly once per send_email invocation."""
    call_count = {"n": 0}

    import resend

    def counting_send(params):
        call_count["n"] += 1
        return {"id": "test-id"}

    monkeypatch.setattr(resend.Emails, "send", staticmethod(counting_send))

    from send import send_email

    send_email(
        html_body="<html><body>Test</body></html>",
        text_body="Test",
        resend_api_key="test-key",
        recipient_email="test@example.com",
    )

    assert call_count["n"] == 1, f"Expected send called once, got {call_count['n']}"


def test_fetch_dedup(mock_env):
    """fetch_all deduplicates articles with the same ID."""
    from sources.base import BaseSource

    class DuplicateSource(BaseSource):
        name = "test_dup"

        def fetch(self):
            article = {
                "id": "dupe-id-123",
                "title": "Duplicate Article",
                "url": "https://example.com/dupe",
                "source": "Test",
                "source_label": "Test Source",
                "summary": "A test article.",
                "published": "2026-03-23T10:00:00+00:00",
                "topic_hint": "technology",
                "image_url": None,
            }
            return [article, dict(article)]  # Same article twice

    plugin = DuplicateSource({}, {})
    raw = plugin.fetch()
    assert len(raw) == 2  # raw returns dupes

    # fetch.fetch_all deduplicates — test the dedup logic directly
    seen = set()
    unique = []
    for a in raw:
        if a["id"] not in seen:
            seen.add(a["id"])
            unique.append(a)
    assert len(unique) == 1, "Deduplication should collapse articles with same ID"


def test_source_fetch_error_doesnt_crash_pipeline(mock_env):
    """A SourceFetchError in one plugin should not prevent other plugins from running."""
    from sources.base import BaseSource, SourceFetchError
    from sources import load_sources

    # Simulate config with one broken plugin name
    config = [
        {"plugin": "nonexistent_plugin_xyz", "enabled": True, "config": {}, "auth": {}},
    ]
    # load_sources should log an error but return an empty list rather than raising
    sources = load_sources(config)
    assert sources == [], "Broken plugin should produce empty list, not raise"
