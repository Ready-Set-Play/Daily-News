# PRD: Extensible Source Plugin System + Test Suite
**Version:** 1.0
**Date:** 2026-03-23
**Owner:** Tim Burlowski
**Status:** Draft — Sprint 2

---

## Executive Summary

Refactor the daily-brief source layer from hardcoded fetch functions into a **plugin architecture** where each source is a self-contained module. Adding a new source (API or RSS) requires creating one file and one config entry — no changes to core pipeline code. Simultaneously introduce a pytest test suite so public contributors can validate their plugins without hitting live APIs. This positions daily-brief as a genuinely extensible open-source project rather than a personal script.

**Core value:** A contributor wanting to add The Guardian, Hacker News, or a custom internal API writes ~50 lines in one file, runs the tests, and opens a PR — without reading or modifying any other code.

---

## Problem Statement

### Current State
- All sources live in a single `fetch.py` (350+ lines): NYT, Google News, Reddit, XKCD, podcasts are all hardcoded functions
- Adding a source means editing core pipeline code — risky, unfriendly to contributors
- No tests: changes break silently, contributors have no way to validate their work
- API tokens are referenced directly in fetch functions — no standard contract for auth

### Impact
- **For Tim:** Adding Bloomberg, Hacker News, or a new RSS feed requires reading 350 lines of code
- **For contributors:** No clear extension point; no tests to catch regressions
- **For CI/CD:** Tests would block bad PRs before they reach the pipeline

---

## Goals & Success Metrics

| Priority | Goal | Metric | Target |
|----------|------|--------|--------|
| P0 | Adding a source = one new file | Files touched to add a source | 1 (plugin file) + config |
| P0 | Test suite runs in CI | GitHub Actions test job | Passes on every PR |
| P0 | No live network calls in tests | Network blocked in CI test job | 0 external calls |
| P1 | Existing sources ported to plugins | Parity with current fetch.py | All 5 source types ported |
| P1 | Plugin API documented | README contributor section | Complete |
| P2 | Token auth is standardized | Auth interface | Consistent across all API plugins |

**Non-goals:**
- Dynamic plugin loading via entry_points / setuptools (overkill for this project size)
- A plugin registry or marketplace
- GUI for managing sources
- Changing the scoring, summarization, or email pipeline
- Supporting non-Python plugins

---

## User Personas

**Tim — Owner/Operator**
Wants to add new sources (e.g., FT RSS, Hacker News) without digging into internals. Runs the digest daily; values stability. Will review PRs from contributors.

**OSS Contributor**
Discovers daily-brief on GitHub, wants to add their favorite source. Needs clear plugin interface, working examples, and tests they can run locally before submitting a PR.

**Future Self (Tim, 6 months later)**
Has forgotten how the code works. Needs tests to safely refactor, and clear plugin contracts to remember how sources are added.

---

## Architecture Design

### Plugin Interface (ABC)

Each source is a class in `src/sources/` that inherits from `BaseSource`:

```python
# src/sources/base.py
from abc import ABC, abstractmethod

class BaseSource(ABC):
    """
    Contract all source plugins must fulfill.
    Implement fetch() to return a list of article dicts.
    """
    name: str          # e.g., "nyt", "hackernews"
    requires_auth: bool = False

    @abstractmethod
    def fetch(self) -> list[dict]:
        """
        Fetch articles. Must return list of dicts with at least:
          id, title, url, source, source_label, summary,
          published, topic_hint, image_url
        Raise SourceFetchError on failure (pipeline will skip + warn).
        """
        ...

    def is_configured(self) -> bool:
        """Return False if required credentials are missing."""
        return True
```

### Plugin Discovery (Config-Driven)

Sources are registered in `config/sources.yaml` — no code changes needed to enable/disable:

```yaml
sources:
  - plugin: nyt
    enabled: true
    auth:
      api_key_env: NYT_API_KEY
    config:
      sections: [technology, science, world, politics]

  - plugin: google_news
    enabled: true
    config:
      queries: { ... }

  - plugin: hackernews          # New source — just add this block
    enabled: true
    config:
      min_score: 200
      categories: [ask_hn, show_hn]

  - plugin: custom_rss
    enabled: false              # Easy on/off toggle
    config:
      feeds:
        - name: "Financial Times"
          url: "https://www.ft.com/rss/home/us"
          topic: markets
```

### Plugin Loader

```python
# src/sources/__init__.py
def load_sources(config: list[dict]) -> list[BaseSource]:
    """Dynamically import and instantiate enabled source plugins."""
    sources = []
    for entry in config:
        if not entry.get("enabled", True):
            continue
        plugin_name = entry["plugin"]
        module = importlib.import_module(f"sources.{plugin_name}")
        cls = getattr(module, "Source")  # Convention: class is always named "Source"
        sources.append(cls(entry.get("config", {}), entry.get("auth", {})))
    return sources
```

### Source Plugin File Convention

```
src/sources/
├── base.py              # BaseSource ABC + SourceFetchError
├── __init__.py          # load_sources() loader
├── nyt.py               # NYT API plugin
├── google_news.py       # Google News RSS plugin
├── reddit.py            # Reddit JSON plugin
├── xkcd.py              # XKCD plugin
├── podcasts.py          # Podcast RSS plugin
└── hackernews.py        # Example new plugin
```

Each plugin file exports exactly one class named `Source` that inherits `BaseSource`.

---

## Functional Requirements

### FR-001 — BaseSource Contract
`BaseSource` SHALL define `fetch() -> list[dict]` as an abstract method with documented return schema. All plugins MUST inherit from it.
**Acceptance:** `isinstance(plugin, BaseSource)` is True for all loaded plugins.

### FR-002 — Config-Driven Registration
Sources SHALL be enabled/disabled by setting `enabled: true/false` in `sources.yaml`. No code change required.
**Acceptance:** Setting `enabled: false` on any source skips it without error.

### FR-003 — Auth Standardization
API-authenticated plugins SHALL read credentials from environment variables named in `auth.api_key_env`. Tokens are never hardcoded.
**Acceptance:** Removing an env var causes `is_configured()` to return False and logs a warning; pipeline continues with other sources.

### FR-004 — Fetch Isolation
A plugin that raises an exception during `fetch()` SHALL NOT crash the pipeline. The loader catches `SourceFetchError`, logs it, and skips that source.
**Acceptance:** Mocking any plugin to raise SourceFetchError results in a digest with remaining sources.

### FR-005 — Backwards Compatibility
All existing sources (NYT, Google News, Reddit, XKCD, podcasts) SHALL be ported to plugins with identical output schema.
**Acceptance:** Digest output is identical before and after refactor (same fields on each article dict).

### FR-006 — Test Suite: Zero External Calls
The full test suite SHALL run with no live network access and incur zero API cost. Three stub layers enforce this:

1. **HTTP (source plugins):** VCR cassettes replay recorded responses. Cassettes are committed to the repo. `pytest-recording` records on first run against real APIs; subsequent runs are fully offline.
2. **Anthropic API (score + summarize):** `unittest.mock.patch` replaces `anthropic.Anthropic` with a fixture that returns deterministic canned responses. No real Claude calls, no token cost.
3. **Resend (send):** `resend.Emails.send` is patched to return `{"id": "test-id"}`. No emails sent during tests.

**Acceptance:** `pytest tests/ --block-network` passes with `ANTHROPIC_API_KEY=test` and `RESEND_API_KEY=test` set. No real credentials required to run the suite.

### FR-007 — Test Suite: Plugin Unit Tests
Each source plugin SHALL have a corresponding test file in `tests/sources/` using VCR cassettes for HTTP. Tests verify: correct article count, required fields present, `is_nyt` flag set where applicable, graceful handling of null fields (e.g., `"multimedia": null`).
**Acceptance:** One test file per plugin; all pass offline.

### FR-008 — Test Suite: Pipeline Smoke Test
`tests/test_pipeline.py` SHALL exercise the full `fetch → score → summarize → render → send` pipeline using:
- Fixture articles from `tests/fixtures/sample_articles.json` (bypasses real fetch)
- Patched Anthropic client returning canned score/summary JSON
- Patched `resend.Emails.send`

Verifies: rendered HTML contains expected section headers, NYT logo present when NYT articles included, feedback URLs injected, send called exactly once.
**Acceptance:** Runs in < 5 seconds, no API calls, no email sent.

### FR-009 — Test Suite: Plugin Contract Tests
A parametrized test SHALL load every enabled plugin, call `fetch()` against its VCR cassette, and assert all returned dicts contain `REQUIRED_FIELDS` with correct types.
**Acceptance:** Adding a plugin that omits `source_label` or returns wrong types fails immediately.

### FR-010 — Contributor Documentation
A `CONTRIBUTING.md` SHALL document the plugin interface with a minimal working example (custom RSS source, ~30 lines).
**Acceptance:** A developer can add a working custom RSS plugin by reading only `CONTRIBUTING.md`.

### FR-011 — CI Test Job
`.github/workflows/` SHALL include a `test.yml` workflow that runs `pytest` on every push and PR.
**Acceptance:** A PR with a broken plugin fails CI before review.

---

## Article Dict Schema (Enforced by Contract Tests)

```python
REQUIRED_FIELDS = {
    "id": str,           # sha256 prefix, stable across runs
    "title": str,
    "url": str,
    "source": str,       # e.g., "NYT", "Reddit"
    "source_label": str, # e.g., "New York Times (Technology)"
    "summary": str,      # raw summary (pre-Claude)
    "published": str,    # ISO 8601
    "topic_hint": str | None,
    "image_url": str | None,
}
```

---

## Implementation Phases

### Phase 1 — Plugin Infrastructure (No behavior change)
- [ ] Create `src/sources/base.py` with `BaseSource` ABC and `SourceFetchError`
- [ ] Create `src/sources/__init__.py` with `load_sources()`
- [ ] Port existing fetch functions to plugin classes (one file each)
- [ ] Update `fetch.py` → thin wrapper that calls `load_sources()` + returns combined list
- [ ] Update `config/sources.yaml` with new plugin registration format
- [ ] Verify digest output identical to pre-refactor

### Phase 2 — Test Suite
- [ ] Add `pytest pytest-recording vcrpy` to `requirements.txt`
- [ ] `tests/conftest.py` — shared fixtures:
  - `mock_anthropic` — patches `anthropic.Anthropic` with canned score/summary responses
  - `mock_resend` — patches `resend.Emails.send` to return `{"id": "test-id"}`
  - `sample_articles` — loads `tests/fixtures/sample_articles.json`
  - `mock_env` — sets dummy `ANTHROPIC_API_KEY`, `RESEND_API_KEY`, `RECIPIENT_EMAIL`
- [ ] `tests/fixtures/sample_articles.json` — 20 realistic article dicts (mix of sources/topics)
- [ ] `tests/sources/` — one test file per plugin; VCR cassettes recorded once, committed
- [ ] `tests/test_plugin_contract.py` — parametrized schema validation against all plugins
- [ ] `tests/test_pipeline.py` — full pipeline smoke test using all three stubs; zero API calls
- [ ] `.github/workflows/test.yml` — CI job; sets `ANTHROPIC_API_KEY=test RESEND_API_KEY=test`

### Phase 3 — New Source Example
- [ ] `src/sources/hackernews.py` — Hacker News Algolia API plugin (no auth required)
- [ ] `tests/sources/test_hackernews.py` with VCR cassettes
- [ ] Add to `config/sources.yaml` (enabled: false by default)
- [ ] Use as reference implementation in `CONTRIBUTING.md`

### Phase 4 — Documentation
- [ ] `CONTRIBUTING.md` — plugin interface guide + walkthrough
- [ ] Update `SETUP.md` — document how to enable/disable sources
- [ ] Docstrings on `BaseSource` methods

---

## Test Structure

```
tests/
├── conftest.py                    # mock_anthropic, mock_resend, sample_articles fixtures
├── sources/
│   ├── cassettes/                 # VCR HTTP recordings (committed, never re-recorded in CI)
│   │   ├── test_nyt_fetch.yaml    # Strip auth headers before committing
│   │   ├── test_google_news_fetch.yaml
│   │   ├── test_reddit_fetch.yaml
│   │   ├── test_xkcd_fetch.yaml
│   │   ├── test_podcasts_fetch.yaml
│   │   └── test_hackernews_fetch.yaml
│   ├── test_nyt.py
│   ├── test_google_news.py
│   ├── test_reddit.py
│   ├── test_xkcd.py
│   ├── test_podcasts.py
│   └── test_hackernews.py
├── test_plugin_contract.py        # Parametrized: all plugins × all required fields
├── test_pipeline.py               # Full pipeline; uses mock_anthropic + mock_resend
└── fixtures/
    └── sample_articles.json       # 20 realistic article dicts for pipeline tests
```

### Stub Design

```python
# conftest.py — key fixtures

@pytest.fixture
def mock_anthropic(monkeypatch):
    """Replaces anthropic.Anthropic with a fake that returns canned JSON.
    Score response: assigns score=75, topic='technology' to every article.
    Summary response: returns 'Test summary.' for every article.
    Zero API calls, zero cost."""

@pytest.fixture
def mock_resend(monkeypatch):
    """Patches resend.Emails.send to return {"id": "test-id"}.
    No emails sent during tests."""

@pytest.fixture
def mock_env(monkeypatch):
    """Sets dummy credentials so pipeline doesn't abort on missing env vars."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    monkeypatch.setenv("RESEND_API_KEY", "test")
    monkeypatch.setenv("RECIPIENT_EMAIL", "test@example.com")
    monkeypatch.setenv("NYT_API_KEY", "test")
```

### Recording VCR Cassettes (one-time, contributor workflow)

```bash
# First time only — requires real API keys:
pytest tests/sources/test_nyt.py --record-mode=once

# Cassette is saved to tests/sources/cassettes/test_nyt_fetch.yaml
# Commit it. All future runs (local + CI) replay from cassette.

# CI always runs in replay-only mode (no credentials needed):
pytest tests/ --block-network
```

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Plugin refactor breaks existing sources | Medium | High | Phase 1 ends with "golden output" comparison test |
| VCR cassettes contain API keys | Low | High | `vcr_config` fixture strips auth headers before cassette write |
| Contributors add plugins with different article schema | Medium | Medium | Contract test (FR-008) fails CI before merge |
| `importlib` dynamic loading fails on bad plugin name | Low | Medium | Loader wraps import in try/except, logs clear error |
| Test suite slows down local dev | Low | Low | `pytest -m unit` tag for fast subset; VCR makes tests instant |

---

## PRD Self-Score

| Dimension | Score | Notes |
|-----------|-------|-------|
| AI-Specific Optimization (25 pts) | 20/25 | Plugin contract tests and schema enforcement well-specified; less emphasis on AI-specific auth patterns |
| Traditional PRD Core (25 pts) | 24/25 | Strong problem/goals/personas; non-goals crisp |
| Implementation Clarity (30 pts) | 28/30 | Full file structure, class interface, config format, and test structure specified; ready to implement |
| Completeness (20 pts) | 19/20 | All user requirements covered; Hacker News as reference plugin grounds the abstractions |
| **Total** | **91/100** | |

---

*Generated by Claude Code · Source Plugin System PRD v1.0 · 2026-03-23*
