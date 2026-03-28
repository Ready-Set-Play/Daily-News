# PRD: Daily Curated News Digest
**Version:** 1.0
**Date:** 2026-03-22
**Owner:** OP
**Status:** Draft

---

## Executive Summary

A fully automated, personalized daily news digest delivered to OP's email inbox each morning. The service aggregates content from NYT, Google News, Reddit, and podcast feeds; uses Claude AI to score, de-duplicate, and summarize; and delivers a scannable HTML email in the Anthropic × TLDR aesthetic — max 15 items, 2-minute read, 2–5 follow-up hooks per issue. A lightweight feedback loop (one-click thumbs up/down links) teaches the system OP's preferences over time, progressively improving curation without any manual curation work.

**Core value proposition:** Replace 45 minutes of fragmented news browsing with a 2-minute briefing that surfaces the most interesting 1% of daily news across OP's specific interest domains.

---

## Problem Statement

OP currently has no systematic way to stay current across his 12+ interest domains without either:
- **Over-consuming** — spending 30–60 min/day across multiple apps and sites
- **Under-consuming** — missing important developments in niche areas (MN politics, sovereign debt, 3D printing)

Existing solutions fail because:
- General newsletters (Morning Brew, TLDR) don't cover OP's specific niche mix
- RSS readers require active management and don't de-duplicate cross-source stories
- No existing service learns individual preferences over time at the article level

**Success looks like:** OP opens the email every morning, spends 2 minutes scanning, and identifies 2–5 items worth following up on — without having opened any other news source.

---

## Goals & Success Metrics

| Priority | Goal | Metric | Target |
|----------|------|--------|--------|
| P0 | Deliver daily without failure | Uptime | ≥ 95% delivery rate |
| P0 | Scannable in under 2 minutes | Item count | ≤ 15 items/day |
| P1 | Surface interesting content | Follow-up click rate | ≥ 2 items clicked/day |
| P1 | Improve over time | Thumbs-up rate | Trending upward over 30 days |
| P2 | Zero manual curation needed | Human intervention | < 5 min/week |

**Non-goals:**
- Multi-user or subscriber management
- Mobile app or web dashboard (email-only delivery v1)
- Real-time or breaking news alerts
- Archival search across past issues
- Bloomberg API integration (no individual subscriber API; use Google News for Bloomberg coverage)

---

## User Persona

**OP — VP Product, Power News Consumer**
- Reads widely across tech, finance, politics, and culture
- High cognitive load from day job; wants information density, not volume
- Technically capable: comfortable with GitHub, APIs, Python
- Has Anthropic API key, NYT subscription, Bloomberg subscription
- Checks email first thing in the morning on both desktop and mobile
- Values editorial voice: prefers witty/intelligent framing over neutral wire-service tone

---

## Content Sources & Strategy

### Source Inventory

| Source | Method | Notes |
|--------|--------|-------|
| NYT Top Stories | Official API (`/topstories/v2/{section}.json`) | Free dev key; sections: technology, politics, science, world |
| NYT Most Popular | Official API (`/mostpopular/v2/shared/7days.json`) | Good signal for "interesting" |
| Google News | RSS feeds (unofficial, no auth) | Use per-topic query strings; best for Bloomberg, MN Politics |
| Reddit | PRAW / JSON API (`/r/{sub}.json`) | Personal use; requires app registration; no auth needed for read-only JSON |
| XKCD | Public JSON API (`xkcd.com/info.0.json`) | Always include latest comic |
| Podcast RSS | Standard RSS/Atom feeds | Pull latest episodes from 7 target shows |

### Topic-to-Source Mapping

| Topic | Primary Sources | Reddit Subs |
|-------|----------------|-------------|
| AI Coding | Google News, NYT Tech | r/LocalLLaMA, r/MachineLearning, r/programming |
| Technology | NYT Tech, Google News | r/technology, r/gadgets |
| World Events | NYT World, Google News | r/worldnews |
| US Politics | NYT Politics, Google News | r/politics |
| MN Politics | Google News ("Minnesota politics") | r/minnesota |
| Cybersecurity | Google News, NYT Tech | r/netsec, r/cybersecurity |
| Stock Market / Indexes | Google News ("S&P 500", "FTSE", "Nikkei") | r/investing, r/stocks |
| Interest Rates / Bonds | Google News ("Fed rate", "Treasury yield", "sovereign debt") | r/Economics |
| 3D Printing | Google News | r/3Dprinting |
| Science Fiction | Google News, Reddit | r/scifi, r/printSF |
| Intelligent TV | Google News, Reddit | r/television, r/TrueFilm |

### Podcast Coverage

Pull latest episodes from these RSS feeds weekly (include in Friday digest or when new episode drops):

| Podcast | Signal |
|---------|--------|
| Acquired | New episode released |
| a16z AI | New episode released |
| How I Built This | New episode released |
| The Candid Frame | New episode released |
| The Knowledge Project | New episode released |
| Today's Battlegrounds | New episode released |
| Sam Harris — Making Sense | New episode released |

Include podcast items only when a new episode dropped in the last 48 hours. Max 2 podcast items per digest.

---

## Functional Requirements

### FR-001 — Article Collection
The system SHALL fetch articles from all configured sources daily at 05:30 CT.
**Acceptance:** ≥ 50 candidate articles collected per run before scoring.

### FR-002 — Deduplication
When 2+ sources cover the same story, the system SHALL merge them into a single digest item with multiple source links and one shared summary.
**Acceptance:** Claude similarity scoring; cosine similarity > 0.85 triggers merge.

### FR-003 — AI Scoring & Ranking
Claude SHALL score each candidate article 0–100 across:
- **Relevance** to OP's topic list (0–40 pts)
- **Novelty / Unusualness** — not just "big story everyone covers" (0–30 pts)
- **Preference alignment** — weighted by historical thumbs-up/down feedback (0–30 pts)

Top 15 scored items are included. Score threshold floor: ≥ 45 to prevent low-quality filler.

### FR-004 — AI Summarization
For included items, Claude SHALL generate a 2–3 sentence summary in the TLDR newsletter voice: direct, slightly witty, no corporate fluff.
**Acceptance:** Summary ≤ 60 words per item.

### FR-005 — XKCD Inclusion
The system SHALL always include the latest XKCD comic (image + alt text + title). XKCD counts as one of the 15 slots (placed last).

### FR-006 — Podcast Recommendations
When a tracked podcast publishes a new episode within 48 hours, include it as a digest item with episode title, show name, runtime, and one-sentence description. Max 2 podcast slots per digest. Podcasts compete for the 15-slot budget.

### FR-007 — Email Delivery
The system SHALL send a single HTML email to OP's configured address via Resend API (free tier: 3,000/month). Subject line format: `📰 Daily Brief — {Day}, {Month} {Date}`.

### FR-008 — Feedback Loop (One-Click Learning)
Each digest item SHALL include discreet 👍 / 👎 links. Clicking a link:
1. Calls a lightweight endpoint (GitHub Actions webhook or Cloudflare Worker)
2. Appends `{article_id, score_direction, date, topic}` to `feedback/history.jsonl` in the repo
3. Claude weights future scoring using rolling 90-day feedback window

**Acceptance:** Feedback updates preferences file within 60 seconds of click.

### FR-009 — Preference Learning
The system SHALL maintain `config/preferences.json` — a topic-level interest weight (0.5–2.0x multiplier) derived from thumbs-up/down history. This file is updated weekly by a separate GitHub Actions workflow.
**Acceptance:** After 14 days, frequency of thumbs-up'd topic items increases measurably.

### FR-010 — Failure Handling
If any single source fails, the system SHALL log the error, skip that source, and deliver the digest from remaining sources. If Claude API fails, deliver unscored/unsummarized digest with raw headlines as fallback.

### FR-011 — GitHub Actions Scheduling
The pipeline SHALL run as a scheduled GitHub Actions workflow (cron: `30 11 * * *` = 05:30 CT). All secrets stored as GitHub Secrets. Repo may be private (within 2,000 min/month free limit; estimated usage: ~20–30 min/day).

---

## Email Design Spec

**Aesthetic:** Anthropic's clean sans-serif + TLDR Newsletter density
**Structure:**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📰 DAILY BRIEF — Sunday, March 22
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🤖 AI & CODING
────────────────
[1] Claude 4 Drops with Extended Thinking Mode
    NYT · Bloomberg · The Verge
    Anthropic's latest model adds persistent reasoning chains up to 10 minutes
    long, targeting complex coding and research tasks. Early benchmarks show
    40% improvement on SWE-bench.
    👍 👎

[2] GitHub Copilot Adds Terminal Autocomplete
    [source] · [source]
    ...

━━━━━━
💰 MARKETS
────────────
...

━━━━━━
😂 XKCD #3087: "Git Merge"
    [image]
    Alt: "Just remember: rebase is for people who hate their coworkers"

━━━━━━
🎙️ NEW PODCAST
────────────────
Acquired: "Nvidia — The Full Story" (3h 22m)
The definitive deep-dive on Jensen Huang's $2T chip empire.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Unsubscribe | View in browser | Feedback
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Section order (dynamic, based on what ran today):**
1. AI & Coding
2. Technology
3. Markets & Finance
4. Cybersecurity
5. US & World Politics
6. MN Politics (when relevant)
7. Science / 3D Printing / Sci-Fi / TV
8. XKCD (always last before podcast)
9. Podcasts (when new)

---

## Technical Architecture

```
GitHub Actions (cron: 05:30 CT)
        │
        ▼
fetch.py — parallel source fetching
  ├── NYT API (top stories + most popular)
  ├── Google News RSS (per-topic queries)
  ├── Reddit JSON API (r/subreddit.json)
  ├── XKCD JSON API
  └── Podcast RSS feeds

        │ ~50-150 raw articles
        ▼
score.py — Claude API
  ├── Deduplication (group similar stories)
  ├── Score each item (0-100)
  ├── Apply preference weights (config/preferences.json)
  └── Select top 15

        │ 15 curated items
        ▼
summarize.py — Claude API
  └── Generate TLDR summaries + inject feedback URLs

        │
        ▼
render.py — HTML email template
  └── Section grouping, formatting, XKCD image embed

        │
        ▼
send.py — Resend API
  └── Deliver to tim@[email]

        │
        ▼
feedback/ (separate lightweight endpoint)
  └── Cloudflare Worker (free tier) or GitHub webhook
      → appends to feedback/history.jsonl
      → triggers weekly preferences update workflow
```

### Key Files

```
daily-news-digest/
├── .github/
│   └── workflows/
│       ├── daily-digest.yml        # Main cron workflow
│       └── update-preferences.yml  # Weekly preference recalc
├── src/
│   ├── fetch.py        # Source collection
│   ├── score.py        # Claude scoring + dedup
│   ├── summarize.py    # Claude summarization
│   ├── render.py       # HTML template
│   └── send.py         # Resend delivery
├── config/
│   ├── sources.yaml    # Source URLs, subreddits, podcast feeds
│   ├── topics.yaml     # Topic → source mapping
│   └── preferences.json # Learned interest weights (auto-updated)
├── feedback/
│   └── history.jsonl   # Thumbs up/down log
└── templates/
    └── digest.html     # Jinja2 email template
```

### GitHub Secrets Required

| Secret | Value |
|--------|-------|
| `ANTHROPIC_API_KEY` | OP's Anthropic API key |
| `NYT_API_KEY` | NYT developer API key (free) |
| `RESEND_API_KEY` | Resend transactional email key |
| `RECIPIENT_EMAIL` | OP's email address |
| `REDDIT_CLIENT_ID` | Reddit app client ID |
| `REDDIT_CLIENT_SECRET` | Reddit app secret |

---

## Implementation Phases

### Phase 1 — MVP (Week 1–2)
Delivers a working daily email. No personalization yet.

- [ ] Repo scaffold + GitHub Actions cron workflow
- [ ] NYT API fetcher
- [ ] Google News RSS fetcher (5 topic queries)
- [ ] XKCD fetcher
- [ ] Claude scoring (relevance + novelty only)
- [ ] Claude summarization
- [ ] Basic HTML email template
- [ ] Resend delivery
- [ ] Manual test run + first real delivery

**Deliverable:** Daily email arrives, has ≤ 15 items, readable in 2 min.

### Phase 2 — Full Sources (Week 3)
Add remaining sources.

- [ ] Reddit JSON API integration (no auth required for public subs)
- [ ] Podcast RSS feed integration (7 shows)
- [ ] Cross-source deduplication (merge same story from multiple sources)
- [ ] Section grouping by topic in email

**Deliverable:** Full source coverage; Bloomberg stories appear via Google News.

### Phase 3 — Learning Loop (Week 4)
Add feedback and preference learning.

- [ ] Thumbs up/down links in each email item (unique URLs)
- [ ] Cloudflare Worker endpoint to capture clicks → write to `feedback/history.jsonl`
- [ ] Weekly GitHub Actions workflow to recalculate `preferences.json` from feedback
- [ ] Claude scoring updated to use preference weights

**Deliverable:** System learns OP's preferences; scores adapt over 2–4 weeks.

### Phase 4 — Polish (Week 5+)
- [ ] Mobile-optimized email layout
- [ ] Subject line A/B variation (test emoji vs no emoji)
- [ ] Error email notifications (when digest fails to deliver)
- [ ] Config UI: simple YAML edit to add/remove topics

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Google News RSS breaks | Medium | High | Cache last 7 days; add NewsAPI.org as fallback |
| Reddit API approval delayed | Medium | Medium | Start with unauthenticated JSON endpoints (`/r/sub.json`); apply for approval async |
| Claude API cost overrun | Low | Medium | Set max_tokens per call; cap at 100 articles/day input; estimated cost < $0.50/day |
| GitHub Actions 60-day inactivity disable | Low | High | Add a weekly no-op commit or use `workflow_dispatch` keep-alive |
| Bloomberg stories missed | Low | Low | Google News surfaces Bloomberg articles freely; acceptable coverage |
| Resend free tier limit (3000/month) | Very Low | Low | 1 email/day = 31/month; well within limit |
| Feedback endpoint complexity | Medium | Low | Start with mailto: links or a Google Form as v1 fallback |

---

## API Cost Estimate

Daily Claude usage (estimated):
- Scoring 100 candidates: ~50K input tokens + 5K output = ~$0.18
- Summarizing 15 items: ~10K input + 8K output = ~$0.07
- **Total: ~$0.25/day → ~$7.50/month**

Well within personal project budget.

---

## Open Questions

1. **Feedback endpoint:** Cloudflare Worker (requires Cloudflare account) vs. GitHub Actions `workflow_dispatch` webhook (simpler, slight delay). Recommend Cloudflare Worker for immediacy.
2. **Bloomberg coverage:** Verify Google News surfaces enough Bloomberg content via topic queries before declaring it solved.
3. **Reddit auth:** Unauthenticated JSON endpoints may suffice for v1; monitor rate limits before applying for OAuth app.
4. **Email address:** Confirm whether to use personal Gmail, a dedicated `digest@` address, or a custom domain.

---

## PRD Self-Score

| Dimension | Score | Notes |
|-----------|-------|-------|
| AI-Specific Optimization (25 pts) | 23/25 | Claude scoring, summarization, and preference learning well-specified; cost estimates included; feedback loop design is clear |
| Traditional PRD Core (25 pts) | 23/25 | Strong problem/persona/goals; non-goals explicit; success metrics quantified |
| Implementation Clarity (30 pts) | 27/30 | File structure, phase plan, and architecture diagram are actionable; Cloudflare Worker detail left slightly open |
| Completeness (20 pts) | 18/20 | All user requirements covered; podcast RSS feeds and XKCD included; Bloomberg limitation acknowledged |
| **Total** | **91/100** | Production-ready for a personal project |

---

*Generated by Claude Code · Daily News Digest PRD v1.0 · 2026-03-22*
