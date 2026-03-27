# Daily Brief

A self-hosted, AI-curated daily news digest delivered to your inbox each morning. Aggregates articles from NYT, Google News, Reddit, podcast feeds, and XKCD; uses Claude AI to score, deduplicate, and summarize; and sends a scannable HTML email — max 15 items, 2-minute read.

**Runs free on GitHub Actions.** You bring the API keys. No servers to manage.

```
DAILY BRIEF — Tuesday, March 24

AI & CODING ─────────────────────────────────────────────
[1] Claude 4 Drops with Extended Thinking Mode
    NYT · The Verge
    Anthropic's latest adds persistent reasoning chains for complex coding
    and research tasks. Early benchmarks: 40% improvement on SWE-bench.
    [+] [-]

MARKETS ──────────────────────────────────────────────────
[2] Fed Signals Two Cuts in 2026 Amid Stubborn Core Inflation
    ...

XKCD #3091: "Dependency Hell"   [always included]
```

---

## How It Works

```
GitHub Actions (cron: 05:30 CT)
        │
        ▼
fetch.py  ── NYT API, Google News RSS, Reddit, Podcasts, XKCD
        │  ~50–150 raw articles
        ▼
score.py  ── Claude scores 0–100 (relevance + novelty + your preferences)
        │  top 15 selected
        ▼
summarize.py  ── Claude writes TLDR summaries
        ▼
render.py  ── HTML email, grouped by topic
        ▼
send.py  ── Resend API delivers to your inbox
```

A lightweight feedback loop (thumbs up/down links in each email) records your preferences and progressively improves curation over time.

**Estimated cost:** ~$0.25/day in Claude API credits (~$7.50/month).

---

## Deploying with GitHub Actions

### Step 1 — Fork and push

Fork this repo (or clone it and push to your own GitHub account):

```bash
git clone https://github.com/YOUR_USERNAME/daily-brief.git
cd daily-brief
git remote set-url origin https://github.com/YOUR_USERNAME/daily-brief.git
git push -u origin main
```

> **Public vs. private:** Public repos get unlimited free GitHub Actions minutes. Private repos get 2,000 free minutes/month — the digest uses ~20–30 min/day, well within that limit.

### Step 2 — Get your API keys

| Service | Where to get it | Cost |
|---------|----------------|------|
| **Anthropic** | console.anthropic.com → API Keys | ~$7.50/month |
| **NYT** | developer.nytimes.com → Create App (enable Top Stories + Most Popular) | Free |
| **Resend** | resend.com → API Keys (verify your sending domain) | Free up to 3,000/month |
| **Reddit** (optional) | reddit.com/prefs/apps → Create App (type: Script) | Free |

Reddit credentials are optional — the pipeline uses Reddit's public JSON API without auth, just with anonymous rate limits.

### Step 3 — Add secrets to GitHub

**Never put API keys in the code or config files.** Instead, store them as GitHub Secrets:

1. Go to your repo on GitHub
2. **Settings → Secrets and variables → Actions → New repository secret**
3. Add each secret from the table below

| Secret Name | Value | Required? |
|-------------|-------|-----------|
| `ANTHROPIC_API_KEY` | Your Anthropic API key | Yes |
| `NYT_API_KEY` | Your NYT developer key | Yes (NYT source) |
| `RESEND_API_KEY` | Your Resend API key | Yes |
| `RECIPIENT_EMAIL` | Your email address | Yes |
| `FROM_EMAIL` | `Daily Brief <digest@yourdomain.com>` | Optional |
| `FEEDBACK_BASE_URL` | Your Cloudflare Worker URL | Optional |
| `REDDIT_CLIENT_ID` | Reddit app client ID | Optional |
| `REDDIT_CLIENT_SECRET` | Reddit app client secret | Optional |

Secrets are **never visible** in logs or to forks of your repo. GitHub automatically redacts them.

### Step 4 — Trigger a test run

1. Go to the **Actions** tab in your repo
2. Click **Daily News Digest → Run workflow**
3. Watch the logs — the pipeline takes 2–5 minutes
4. Check your inbox

If it works, the cron schedule takes over: **11:30 UTC daily** (5:30 AM CT in winter, 6:30 AM CT in summer).

### Step 5 — Adjust the send time (optional)

Edit `.github/workflows/daily-digest.yml`:

```yaml
- cron: "30 11 * * *"   # 11:30 UTC
```

Use [crontab.guru](https://crontab.guru) to find your desired UTC time.

### Step 6 — Set up feedback learning (optional)

The thumbs up/down links in each email need an endpoint to record clicks. Without it, links appear but do nothing — the rest of the digest still works.

**Cloudflare Worker (recommended, free):**

```bash
npm install -g wrangler
wrangler login
cd feedback/
wrangler deploy worker.js --name daily-brief-feedback
```

Set these environment variables in your Cloudflare Worker dashboard:
- `GITHUB_TOKEN` — a GitHub Personal Access Token with `contents:write` scope
- `GITHUB_REPO` — `YOUR_USERNAME/daily-brief`
- `GITHUB_BRANCH` — `main`

Then add your Worker URL to GitHub Secrets as `FEEDBACK_BASE_URL`.

---

## Keeping GitHub Actions from Auto-Disabling

GitHub disables scheduled workflows on repos with **60+ days of inactivity**. Options to prevent this:

- The feedback system commits to the repo weekly automatically (if you use it)
- Make any small commit at least once every 60 days
- Manually trigger a run from the Actions tab occasionally

---

## Reading the Logs

Every pipeline run is logged in GitHub Actions:

1. Go to **Actions** tab → **Daily News Digest**
2. Click any run to see the full log
3. Each pipeline step is labeled:

```
=== STEP 1: FETCHING ===
=== STEP 2: SCORING ===
=== STEP 3: SUMMARIZING ===
=== STEP 4: RENDERING ===
=== STEP 5: SENDING ===
=== DIGEST DELIVERED SUCCESSFULLY ===
```

If a single source (e.g., Reddit) fails, the pipeline logs a warning and continues — you still get a digest from the remaining sources. A total failure sends you a notification email automatically.

---

## Protecting Your Keys — What Not to Commit

The `.gitignore` already excludes the most common leakage paths:

```
.env                         # Local credentials
feedback/history.jsonl       # Accumulates personal vote data
```

**Additional rules to follow:**

- **Never hardcode** API keys in `config/sources.yaml`, `src/`, or anywhere in the repo
- **Before committing VCR cassette files** (HTTP recordings for tests), check them for auth headers or `api-key=` query params — replace any real values with `REDACTED`. See the [Contributing](#contributing) section.
- **Use GitHub Secrets** for all credentials — never `.env` files pushed to the repo
- Run `git diff --staged` before every commit and scan for key-like strings

To check a cassette before committing:

```bash
grep -i "api.key\|authorization\|bearer\|token" tests/sources/cassettes/*.yaml
```

---

## Customizing Your Digest

All configuration lives in `config/` — no code changes needed.

**`config/sources.yaml`** — Enable/disable sources and adjust their parameters:

```yaml
- plugin: hackernews
  enabled: true        # ← flip this on
  config:
    min_score: 200
    limit: 20

- plugin: reddit
  enabled: true
  config:
    min_score: 100     # ← raise this to reduce Reddit noise
```

**`config/topics.yaml`** — Change section labels and display order.

**`config/preferences.json`** — Auto-updated weekly by the feedback system. You can also edit this manually to boost or suppress topics (weights are 0.5–2.0x multipliers).

---

## Testing

The test suite runs with **no live network calls and no API cost** — all HTTP responses are pre-recorded in VCR cassette files, and Anthropic/Resend are stubbed out.

### Running tests locally

```bash
# Install dependencies (includes pytest + vcrpy)
pip install -r requirements.txt

# Run everything
./test.sh

# Fast: pipeline smoke tests only (no cassettes needed, ~2 seconds)
./test.sh pipeline

# Record cassettes for a new plugin (requires real API keys in .env)
./test.sh record
```

### What the tests cover

| Test file | What it tests | Network? |
|-----------|--------------|---------|
| `tests/test_pipeline.py` | Full fetch→score→summarize→render→send pipeline | None (fully stubbed) |
| `tests/test_plugin_contract.py` | Every source plugin returns correct field schema | None (VCR cassettes) |
| `tests/sources/test_nyt.py` | NYT plugin specifically | None (VCR cassette) |
| `tests/sources/test_*.py` | Per-plugin unit tests | None (VCR cassettes) |

### Running in CI

Tests run automatically on every push and pull request via `.github/workflows/test.yml`. A PR with a broken plugin fails CI before review. No real credentials are needed — the CI workflow sets dummy values.

### Local preview (render only, no email)

```bash
# Deploy to ~/Scripts/daily-brief and render a preview HTML file
./deploy.sh --render-only

# Then open:
open ~/Scripts/daily-brief/digest_preview.html
```

---

## Troubleshooting

| Symptom | Where to look | Fix |
|---------|--------------|-----|
| No email received | Actions → run log → Step 5 | Verify `RESEND_API_KEY` and sending domain in Resend dashboard |
| "No articles fetched" | Actions → run log → Step 1 | Check `NYT_API_KEY` is valid; Google News RSS may be temporarily down |
| Digest has fewer than 15 items | Actions → run log → Step 2 | Lower `MIN_SCORE` in `src/score.py` (default: 45) |
| Source skipped with warning | Actions → run log | The source failed — pipeline continued. Check the warning message for which source and why |
| XKCD not appearing | Actions → run log | XKCD API is public; check if Actions runner had network access |
| Podcast not appearing | Actions → run log | Verify RSS feed URL in `sources.yaml`; episode must be < 48 hours old |
| Actions workflow disabled | Actions tab shows "disabled" | Re-enable via Actions tab → Enable workflow; make a commit to wake the repo |
| `ANTHROPIC_API_KEY not set` | Actions → run log | Secret is missing or misspelled in Settings → Secrets |
| Test failures locally | `pytest -v` output | See cassette-related errors below |

**Cassette not found:**
If a test fails with `CassetteNotFoundError`, the cassette hasn't been recorded yet. Run `./test.sh record` with real API keys.

**Cassette returns 401:**
A cassette may have been recorded with a key that got redacted. Re-record it: delete the cassette file and run `./test.sh record`.

---

## Contributing

### Adding a new source plugin

Each source is a self-contained file in `src/sources/`. Adding a new one requires exactly one new file and one config entry — no changes to the core pipeline.

**1. Create `src/sources/my_source.py`:**

```python
import hashlib
import logging
import feedparser
from .base import BaseSource, SourceFetchError

logger = logging.getLogger(__name__)

def _make_id(url, title):
    return hashlib.sha256(f"{url}|{title}".encode()).hexdigest()[:16]

class Source(BaseSource):
    name = "my_source"

    def fetch(self) -> list[dict]:
        feed_url = self.config.get("url", "")
        try:
            feed = feedparser.parse(feed_url)
        except Exception as e:
            raise SourceFetchError(f"RSS fetch failed: {e}") from e

        return [{
            "id": _make_id(e.link, e.title),
            "title": e.get("title", ""),
            "url": e.get("link", ""),
            "source": "My Source",
            "source_label": feed.feed.get("title", "My Source"),
            "summary": e.get("summary", ""),
            "published": e.get("published", ""),
            "topic_hint": self.config.get("topic", "technology"),
            "image_url": None,
        } for e in feed.entries[:10] if e.get("link")]
```

**2. Register in `config/sources.yaml`:**

```yaml
- plugin: my_source
  enabled: false       # disabled by default — good practice for new contributions
  config:
    url: "https://example.com/rss"
    topic: technology
```

**3. Write a test with a VCR cassette:**

```bash
# Record once (needs real network access)
pytest tests/sources/test_my_source.py --record-mode=once

# Scan the cassette for secrets before committing
grep -i "api.key\|authorization\|bearer" tests/sources/cassettes/test_my_source_fetch.yaml

# Commit the cassette alongside your plugin
git add tests/sources/cassettes/test_my_source_fetch.yaml
```

See `CONTRIBUTING.md` for the full test template and the complete pre-PR checklist.

### Required article fields

Every dict returned from `fetch()` must include:

| Field | Type | Notes |
|-------|------|-------|
| `id` | `str` | 16-char hash of URL+title — must be stable across runs |
| `title` | `str` | Article headline |
| `url` | `str` | Canonical URL |
| `source` | `str` | Short name, e.g. `"Guardian"` |
| `source_label` | `str` | Display name, e.g. `"The Guardian (Tech)"` |
| `summary` | `str` | Short description or abstract |
| `published` | `str` | ISO 8601 date string |
| `topic_hint` | `str \| None` | Topic key from `topics.yaml` |
| `image_url` | `str \| None` | Article image URL, or `None` |

Extra fields (e.g., `reddit_score`, `is_podcast`) are allowed and passed through the pipeline.

### PR checklist

- [ ] `src/sources/<name>.py` with class named `Source`
- [ ] All 9 required fields returned by `fetch()`
- [ ] `SourceFetchError` raised on failure (not bare exceptions)
- [ ] Entry in `config/sources.yaml` (`enabled: false` is fine)
- [ ] `tests/sources/test_<name>.py` with VCR cassette
- [ ] Cassette scanned for secrets (replace real values with `REDACTED`)
- [ ] `pytest tests/` passes locally

---

## Planned Features

- **Web scraper support** — add a `scraper` plugin type for sites without APIs or RSS feeds, using a headless browser or lightweight HTML parser
- **More sophisticated scheduling** — per-topic delivery windows (e.g., market updates at market open, weekend long-reads digest), timezone-aware cron, and configurable frequency beyond once-daily

---

## Architecture Reference

```
daily-brief/
├── .github/
│   └── workflows/
│       ├── daily-digest.yml        # Main cron: runs at 11:30 UTC daily
│       ├── update-preferences.yml  # Weekly: recalculates preference weights
│       └── test.yml                # CI: runs on every push and PR
├── src/
│   ├── main.py                     # Pipeline orchestrator + CLI (--mode full|dry-run|render-only)
│   ├── fetch.py                    # Loads plugins and collects articles
│   ├── score.py                    # Claude scoring + dedup + preference weighting
│   ├── summarize.py                # Claude TLDR summarization
│   ├── render.py                   # HTML email template (Jinja2)
│   ├── send.py                     # Resend API delivery
│   ├── update_preferences.py       # Recalculates config/preferences.json from feedback
│   └── sources/
│       ├── base.py                 # BaseSource ABC + SourceFetchError
│       ├── __init__.py             # load_sources() dynamic plugin loader
│       ├── nyt.py                  # New York Times API
│       ├── google_news.py          # Google News RSS (per-topic queries)
│       ├── reddit.py               # Reddit public JSON API
│       ├── podcasts.py             # Podcast RSS feeds
│       ├── xkcd.py                 # XKCD (always included)
│       └── hackernews.py           # Hacker News via Algolia (disabled by default)
├── config/
│   ├── sources.yaml                # Plugin registry — enable/disable sources here
│   ├── topics.yaml                 # Topic labels, emoji, display order
│   └── preferences.json            # Learned interest weights (auto-updated)
├── feedback/
│   └── worker.js                   # Cloudflare Worker: captures thumbs up/down clicks
├── tests/
│   ├── conftest.py                 # Shared fixtures: mock_anthropic, mock_resend, mock_env
│   ├── test_pipeline.py            # Full pipeline smoke tests (fully stubbed, ~2s)
│   ├── test_plugin_contract.py     # Parametrized schema validation across all plugins
│   ├── sources/
│   │   ├── cassettes/              # VCR HTTP recordings (committed — no network in CI)
│   │   └── test_*.py               # Per-plugin unit tests
│   └── fixtures/
│       └── sample_articles.json    # 20 realistic article dicts for pipeline tests
├── deploy.sh                       # Local deploy script (syncs to ~/Scripts/daily-brief)
├── test.sh                         # Test runner shortcut
├── requirements.txt
└── .gitignore                      # Excludes .env, feedback/history.jsonl, __pycache__
```
