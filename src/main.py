"""
main.py — Orchestrates the full daily digest pipeline.
Run directly or via GitHub Actions.

Modes:
  full          Fetch, score, summarize, render, send email (default)
  dry-run       Fetch and score only — prints ranked article list, no email
  render-only   Full pipeline except send — saves digest_preview.html locally
  update-prefs  Recalculate preference weights from feedback history

LLM provider is controlled by the LLM_PROVIDER env var (default: anthropic).
Set LLM_PROVIDER=none to run without any LLM (heuristic scoring, raw summaries).
"""

import argparse
import logging
import os
import sys

from fetch import fetch_all, save_sent_history
from score import select_top
from summarize import generate_summaries
from render import render_email
from send import send_email

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def _check_llm_credentials() -> bool:
    """Validate that the required credential for the chosen LLM provider is set."""
    provider = os.environ.get("LLM_PROVIDER", "anthropic").lower()

    if provider == "none":
        return True

    required = {
        "anthropic": ("ANTHROPIC_API_KEY", "Anthropic API key"),
        "openai": ("OPENAI_API_KEY", "OpenAI API key"),
        "ollama": (None, None),  # local, no key needed
    }

    if provider not in required:
        logger.error(
            f"Unknown LLM_PROVIDER '{provider}'. Valid: anthropic, openai, ollama, none"
        )
        return False

    env_var, label = required[provider]
    if env_var and not os.environ.get(env_var):
        logger.error(f"{label} ({env_var}) is required when LLM_PROVIDER={provider}")
        return False

    return True


def run_fetch_and_score(nyt_api_key: str):
    """Shared fetch+score logic used by all modes."""
    logger.info("=== STEP 1: FETCHING ===")
    try:
        articles = fetch_all(nyt_api_key)
        logger.info(f"Fetched {len(articles)} total articles")
    except Exception as e:
        logger.error(f"Fetch step failed: {e}")
        articles = []

    if not articles:
        logger.error("No articles fetched. Aborting.")
        sys.exit(1)

    logger.info("=== STEP 2: SCORING ===")
    try:
        selected = select_top(articles)
        logger.info(f"Selected {len(selected)} articles for digest")
    except Exception as e:
        logger.error(f"Scoring step failed: {e}. Using raw top articles.")
        selected = articles[:15]

    if not selected:
        logger.error("No articles selected. Aborting.")
        sys.exit(1)

    return selected


def mode_full(nyt_api_key, resend_api_key, recipient_email, from_email):
    selected = run_fetch_and_score(nyt_api_key)

    logger.info("=== STEP 3: SUMMARIZING ===")
    try:
        summarized = generate_summaries(selected)
    except Exception as e:
        logger.error(f"Summarization failed: {e}. Using raw summaries.")
        summarized = selected

    logger.info("=== STEP 4: RENDERING ===")
    try:
        html_body, text_body = render_email(summarized)
    except Exception as e:
        logger.error(f"Render step failed: {e}")
        sys.exit(1)

    logger.info("=== STEP 5: SENDING ===")
    success = send_email(
        html_body=html_body,
        text_body=text_body,
        resend_api_key=resend_api_key,
        recipient_email=recipient_email,
        from_email=from_email,
    )
    if success:
        logger.info("=== DIGEST DELIVERED SUCCESSFULLY ===")
        save_sent_history(selected)
    else:
        logger.error("=== DELIVERY FAILED ===")
        sys.exit(1)


def mode_dry_run(nyt_api_key):
    selected = run_fetch_and_score(nyt_api_key)
    print()
    for i, a in enumerate(selected, 1):
        score = a.get("final_score", a.get("claude_score", "?"))
        topic = a.get("ai_topic") or a.get("topic_hint", "")
        print(f"  [{i:2d}] [{score:5.1f}] [{topic:<15}] {a['title'][:70]}")
        print(f"        {a['source_label']}")
    print()


def mode_render_only(nyt_api_key):
    selected = run_fetch_and_score(nyt_api_key)

    logger.info("=== STEP 3: SUMMARIZING ===")
    try:
        summarized = generate_summaries(selected)
    except Exception as e:
        logger.error(f"Summarization failed: {e}. Using raw summaries.")
        summarized = selected

    logger.info("=== STEP 4: RENDERING ===")
    try:
        html_body, _ = render_email(summarized)
    except Exception as e:
        logger.error(f"Render step failed: {e}")
        sys.exit(1)

    out = os.path.join(os.path.dirname(__file__), "..", "digest_preview.html")
    with open(out, "w") as f:
        f.write(html_body)
    abs_path = os.path.abspath(out)
    logger.info(f"Saved to: {abs_path}")
    print(f'\nOpen preview:\n  open "{abs_path}"\n')


def mode_update_prefs():
    from update_preferences import update_preferences

    update_preferences()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Daily Brief — news digest pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
modes:
  full          Fetch, score, summarize, render, send email (default)
  dry-run       Fetch and score only — prints ranked list, no email
  render-only   Full pipeline — saves digest_preview.html, no email
  update-prefs  Recalculate preference weights from feedback history
        """,
    )
    parser.add_argument(
        "--mode",
        choices=["full", "dry-run", "render-only", "update-prefs"],
        default="full",
    )
    args = parser.parse_args()

    nyt_api_key = os.environ.get("NYT_API_KEY", "")
    resend_api_key = os.environ.get("RESEND_API_KEY", "")
    recipient_email = os.environ.get("RECIPIENT_EMAIL", "")
    from_email = os.environ.get("FROM_EMAIL", "")

    if args.mode == "update-prefs":
        mode_update_prefs()
        return 0

    if not _check_llm_credentials():
        return 1

    if not nyt_api_key:
        logger.warning("NYT_API_KEY not set — skipping NYT source")

    if args.mode == "dry-run":
        mode_dry_run(nyt_api_key)

    elif args.mode == "render-only":
        mode_render_only(nyt_api_key)

    elif args.mode == "full":
        missing = []
        if not resend_api_key:
            missing.append("RESEND_API_KEY")
        if not recipient_email:
            missing.append("RECIPIENT_EMAIL")
        if not from_email:
            missing.append("FROM_EMAIL")
        if missing:
            logger.error(f"Missing for full send: {', '.join(missing)}")
            return 1
        mode_full(nyt_api_key, resend_api_key, recipient_email, from_email)

    return 0


if __name__ == "__main__":
    sys.exit(main())
