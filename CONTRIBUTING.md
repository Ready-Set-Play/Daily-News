# Contributing to daily-brief

## Adding a New Source Plugin

Each news source is a self-contained plugin file in `src/sources/`. Adding a new source requires:

1. One new file: `src/sources/<your_source>.py`
2. One config entry in `config/sources.yaml`

That's it. No changes to the core pipeline.

---

## Minimal Plugin Example

Here's a complete custom RSS plugin (~30 lines):

```python
# src/sources/my_rss.py
import hashlib
import logging

import feedparser

from .base import BaseSource, SourceFetchError

logger = logging.getLogger(__name__)


def _make_id(url: str, title: str) -> str:
    return hashlib.sha256(f"{url}|{title}".encode()).hexdigest()[:16]


class Source(BaseSource):
    name = "my_rss"

    def fetch(self) -> list[dict]:
        feed_url = self.config.get("url", "")
        topic = self.config.get("topic", "technology")

        try:
            feed = feedparser.parse(feed_url)
        except Exception as e:
            raise SourceFetchError(f"RSS fetch failed: {e}") from e

        articles = []
        for entry in feed.entries[:10]:
            link = entry.get("link", "")
            if not link:
                continue
            articles.append({
                "id": _make_id(link, entry.get("title", "")),
                "title": entry.get("title", ""),
                "url": link,
                "source": "My RSS",
                "source_label": feed.feed.get("title", "My RSS Feed"),
                "summary": entry.get("summary", ""),
                "published": entry.get("published", ""),
                "topic_hint": topic,
                "image_url": None,
            })

        logger.info(f"my_rss: fetched {len(articles)} articles")
        return articles
```

---

## Required Article Fields

Every dict returned from `fetch()` must include these keys:

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Stable 16-char hash of URL+title |
| `title` | `str` | Article headline |
| `url` | `str` | Canonical article URL |
| `source` | `str` | Short source name, e.g. `"My RSS"` |
| `source_label` | `str` | Display name, e.g. `"My RSS Feed"` |
| `summary` | `str` | Short description or abstract |
| `published` | `str` | ISO 8601 date string |
| `topic_hint` | `str \| None` | Topic key for scoring (see topics.yaml) |
| `image_url` | `str \| None` | Article image URL, or None |

Any additional fields (e.g., `is_podcast`, `reddit_score`) are allowed and will be passed through the pipeline.

---

## Register in sources.yaml

Add an entry to `config/sources.yaml`:

```yaml
- plugin: my_rss
  enabled: true
  config:
    url: "https://example.com/rss"
    topic: technology
```

Set `enabled: false` to ship the plugin disabled by default (good practice for new contributions).

---

## Writing Tests

1. Create `tests/sources/test_my_rss.py`
2. Record a VCR cassette once (requires a live internet connection):
   ```bash
   pytest tests/sources/test_my_rss.py --record-mode=once
   ```
3. Commit the cassette at `tests/sources/cassettes/test_my_rss_fetch.yaml`
4. All future test runs (including CI) replay from the cassette — no network, no cost

**Strip API keys from cassettes before committing.** The cassette file is a YAML file — search for any Authorization or api-key headers and replace with `REDACTED`.

### Minimal test template

```python
import pytest
pytest.importorskip("vcr")
import vcr
from sources.my_rss import Source

CASSETTE = "tests/sources/cassettes/test_my_rss_fetch.yaml"
REQUIRED_FIELDS = {
    "id", "title", "url", "source", "source_label",
    "summary", "published", "topic_hint", "image_url"
}

@vcr.use_cassette(CASSETTE, record_mode="none")
def test_my_rss_returns_articles():
    plugin = Source({"url": "https://example.com/rss", "topic": "technology"}, {})
    articles = plugin.fetch()
    assert len(articles) > 0

@vcr.use_cassette(CASSETTE, record_mode="none")
def test_my_rss_required_fields():
    plugin = Source({"url": "https://example.com/rss", "topic": "technology"}, {})
    articles = plugin.fetch()
    for article in articles:
        for field in REQUIRED_FIELDS:
            assert field in article
```

---

## Running the Full Test Suite

```bash
# Install test dependencies
pip install -r requirements.txt

# Run all tests (offline — cassettes required for source tests)
pytest

# Run just the pipeline smoke tests (no cassettes needed)
pytest tests/test_pipeline.py

# Run just the contract tests (cassettes required)
pytest tests/test_plugin_contract.py
```

The pipeline smoke tests (`test_pipeline.py`) stub out Anthropic and Resend — no API keys needed, no cost.

---

## Authenticated Sources

If your source requires an API key, set `requires_auth = True` and read credentials from environment variables named in `auth.api_key_env`:

```python
class Source(BaseSource):
    name = "my_api"
    requires_auth = True

    def fetch(self) -> list[dict]:
        api_key = os.environ.get(self.auth.get("api_key_env", "MY_API_KEY"), "")
        # use api_key ...
```

```yaml
# sources.yaml
- plugin: my_api
  enabled: true
  auth:
    api_key_env: MY_API_KEY
  config:
    endpoint: "https://api.example.com"
```

The loader will call `is_configured()` before calling `fetch()`. If the env var is missing, the source is skipped with a warning — no crash.

---

## Checklist Before Opening a PR

- [ ] Plugin file at `src/sources/<name>.py` with class named `Source`
- [ ] All 9 required fields returned by `fetch()`
- [ ] `SourceFetchError` raised on failure (not bare exceptions)
- [ ] Entry added to `config/sources.yaml` (disabled by default is fine)
- [ ] Test file at `tests/sources/test_<name>.py`
- [ ] VCR cassette committed at `tests/sources/cassettes/test_<name>_fetch.yaml`
- [ ] No API keys in cassette (replace with `REDACTED`)
- [ ] `pytest tests/` passes locally
