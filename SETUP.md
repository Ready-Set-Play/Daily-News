# Daily Brief — Setup Guide

## Prerequisites

- GitHub account
- Anthropic API key
- Resend account (free at resend.com)
- NYT developer API key (free at developer.nytimes.com)

---

## Step 1 — Create the GitHub Repository

1. Create a new **private** repository on GitHub (or public if you prefer — unlimited free minutes for public repos)
2. Push this entire directory to it:

```bash
git init
git add .
git commit -m "Initial daily brief setup"
git remote add origin https://github.com/YOUR_USERNAME/daily-brief.git
git push -u origin main
```

---

## Step 2 — Get API Keys

### Anthropic API

- Go to console.anthropic.com → API Keys → Create Key
- Estimated cost: ~$7.50/month

### NYT API (Free)

- Go to developer.nytimes.com → Create App
- Enable: Top Stories, Most Popular, Article Search

### Resend (Free — 3,000 emails/month)

- Sign up at resend.com
- Verify your sending domain (or use their sandbox for testing)
- Get your API key from the dashboard

### Reddit (Optional — for better rate limits)

- Go to reddit.com/prefs/apps → Create App
- Type: Script
- Name: daily-brief (personal use)
- Add `REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET` to secrets if you get one
- Without Reddit OAuth: the JSON API still works for public subreddits, just with anonymous rate limits

---

## Step 3 — Set GitHub Secrets

In your repo: Settings → Secrets and variables → Actions → New repository secret

| Secret Name | Value |
|-------------|-------|
| `ANTHROPIC_API_KEY` | Your Anthropic API key |
| `NYT_API_KEY` | Your NYT developer key |
| `RESEND_API_KEY` | Your Resend API key |
| `RECIPIENT_EMAIL` | Your email address |
| `FROM_EMAIL` | `Daily Brief <digest@yourdomain.com>` |
| `FEEDBACK_BASE_URL` | Your Cloudflare Worker URL (Step 5) — or leave blank to skip feedback links |

---

## Step 4 — Test the Pipeline

Trigger a manual run from GitHub Actions:

1. Go to Actions tab → "Daily News Digest" → "Run workflow"
2. Check the logs — should take 2–5 minutes
3. Check your inbox

---

## Step 5 — Set Up Feedback Learning (Optional but Recommended)

The 👍/👎 links in each email need a small endpoint to capture clicks.

### Option A: Cloudflare Worker (Recommended)

1. Sign up at cloudflare.com (free)
2. Install Wrangler CLI: `npm install -g wrangler`
3. In the `feedback/` directory:

```bash
wrangler login
wrangler deploy worker.js --name daily-brief-feedback
```

1. Set Worker environment variables in Cloudflare dashboard:
   - `GITHUB_TOKEN`: A GitHub Personal Access Token with `contents:write` permission
   - `GITHUB_REPO`: `YOUR_USERNAME/daily-brief`
   - `GITHUB_BRANCH`: `main`

2. Add your Worker URL to GitHub Secrets as `FEEDBACK_BASE_URL`
   (e.g., `https://daily-brief-feedback.YOUR_SUBDOMAIN.workers.dev`)

### Option B: Skip feedback for now

Leave `FEEDBACK_BASE_URL` blank. The 👍/👎 links will appear but won't do anything. You can add feedback later.

---

## Step 6 — Configure Your Digest

Edit `config/sources.yaml` to:

- Add/remove subreddits
- Add/remove Google News search queries
- Add podcast RSS feeds
- Adjust the `reddit.min_score` threshold

Edit `config/topics.yaml` to reorder sections or change emoji/labels.

---

## Timing

The digest runs at **11:30 UTC daily**:

- During CST (Nov–Mar): arrives at 5:30 AM CT
- During CDT (Mar–Nov): arrives at 6:30 AM CT

To adjust, edit the cron in `.github/workflows/daily-digest.yml`:

```yaml
- cron: "30 11 * * *"   # 11:30 UTC
```

---

## Preventing GitHub Actions Auto-Disable

GitHub disables scheduled workflows after 60 days of repo inactivity. To prevent this:

- The feedback system commits to the repo weekly (if you use it)
- Otherwise, make a small commit at least once every 60 days, or
- Use `workflow_dispatch` button in Actions to trigger manually occasionally

---

## Troubleshooting

| Problem | Solution |
|---------|---------|
| No email received | Check Actions logs for errors; verify Resend key and domain |
| "No articles fetched" | Check NYT API key is valid; Google News RSS may be temporarily down |
| Digest has fewer than 15 items | Lower `MIN_SCORE` in `src/score.py` (default: 45) |
| XKCD not appearing | XKCD API is public; check network access from Actions runner |
| Podcast not appearing | Verify RSS feed URL is correct and episode is < 48 hours old |
