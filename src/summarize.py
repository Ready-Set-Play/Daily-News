"""
summarize.py — Generate TLDR-voice summaries for each selected article.

When LLM_PROVIDER=none, truncates the existing summary field to 60 words.
Otherwise delegates to the configured LLM provider.
"""

import json
import logging
import os

from llm import load_llm_client

logger = logging.getLogger(__name__)

FEEDBACK_BASE_URL = os.environ.get(
    "FEEDBACK_BASE_URL", "https://your-feedback-worker.workers.dev"
)


def generate_summaries(articles: list[dict]) -> list[dict]:
    """Generate summaries for all articles. Injects feedback URLs."""
    client = load_llm_client()

    needs_summary = [
        a for a in articles if not a.get("is_xkcd") and not a.get("is_podcast")
    ]

    if needs_summary:
        if client.name == "none":
            _truncate_summaries(needs_summary)
        else:
            _batch_summarize(needs_summary, client)

    for a in articles:
        a["feedback_up_url"] = (
            f"{FEEDBACK_BASE_URL}/feedback?id={a['id']}&dir=up&topic={a.get('ai_topic', '')}"
        )
        a["feedback_down_url"] = (
            f"{FEEDBACK_BASE_URL}/feedback?id={a['id']}&dir=down&topic={a.get('ai_topic', '')}"
        )

    return articles


def _truncate_summaries(articles: list[dict]) -> None:
    """Fallback: trim existing summary to 60 words. Modifies in place."""
    for a in articles:
        raw = (a.get("summary") or "").strip()
        words = raw.split()
        a["tldr_summary"] = " ".join(words[:60]) + ("..." if len(words) > 60 else "")


def _batch_summarize(articles: list[dict], client) -> None:
    """Summarize articles in one LLM call. Modifies articles in place."""

    compact = [
        {
            "idx": i,
            "title": a["title"],
            "source": a.get("source_label", a["source"]),
            "existing_summary": (a.get("summary", "") or "")[:300],
        }
        for i, a in enumerate(articles)
    ]

    prompt = f"""You are writing for a sharp, senior tech executive's morning briefing — think Anthropic's design sensibility crossed with TLDR Newsletter energy.

Voice: Direct, slightly witty, no corporate jargon. Write like a smart friend who read the article so you don't have to.
Length: EXACTLY 2-3 sentences. Never more than 60 words per summary.
Tone: Confident. Informative. Occasionally dry. Never breathless or hyped.

Write a summary for each article below. If you don't know the full article content, write the best summary you can from the title and existing snippet.

Articles:
{json.dumps(compact, indent=2)}

Return ONLY a JSON array (no explanation):
[{{"idx": 0, "summary": "Your 2-3 sentence summary here."}}, ...]"""

    try:
        raw = client.complete(prompt, max_tokens=3000)
        start = raw.find("[")
        end = raw.rfind("]") + 1
        summaries = json.loads(raw[start:end]) if start >= 0 else []

        summary_map = {s["idx"]: s["summary"] for s in summaries}
        for i, a in enumerate(articles):
            if i in summary_map:
                a["tldr_summary"] = summary_map[i]
            elif not a.get("tldr_summary"):
                a["tldr_summary"] = a.get("summary", "")

    except Exception as e:
        logger.warning(f"Summarization failed: {e}. Using raw summaries.")
        for a in articles:
            if not a.get("tldr_summary"):
                a["tldr_summary"] = a.get("summary", "No summary available.")


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)
    data = json.load(sys.stdin)
    result = generate_summaries(data)
    print(json.dumps(result, indent=2, default=str))
