"""
score.py — Score, deduplicate, and select the top 15 articles.

When LLM_PROVIDER=none, uses heuristic scoring (no API calls).
Otherwise delegates to the configured LLM provider.
"""

import json
import logging
import os
import random
from typing import Any

import yaml

from llm import LLMClient, load_llm_client

logger = logging.getLogger(__name__)

CONFIG_DIR = os.path.join(os.path.dirname(__file__), "..", "config")
MAX_ITEMS = 15
MIN_SCORE = 45
MAX_PODCAST_ITEMS = 2

# Source reputation weights used by heuristic fallback
_SOURCE_BASE_SCORES = {
    "NYT": 72,
    "Reddit": 55,
    "HackerNews": 65,
    "Google News": 60,
    "Podcast": 70,
}


def load_preferences() -> dict:
    prefs_path = os.path.join(CONFIG_DIR, "preferences.json")
    try:
        with open(prefs_path) as f:
            return json.load(f)
    except Exception:
        return {"topic_weights": {}}


def load_topics() -> list[dict]:
    with open(os.path.join(CONFIG_DIR, "topics.yaml")) as f:
        return yaml.safe_load(f)["sections"]


def deduplicate(articles: list[dict], client: LLMClient) -> list[dict]:
    """
    Group articles covering the same story and merge them.
    Skipped when LLM_PROVIDER=none.
    """
    if client.name == "none":
        return articles

    if len(articles) <= 1:
        return articles

    titles = [
        {"idx": i, "title": a["title"], "source": a.get("source_label", a["source"])}
        for i, a in enumerate(articles)
        if not a.get("is_xkcd") and not a.get("is_podcast")
    ]

    prompt = f"""You are a news deduplication engine. Given the following list of news article titles,
identify groups of articles that cover the SAME story or event.

Return ONLY a JSON array of groups. Each group is an array of indices (from the list below) that cover the same story.
Only include groups with 2+ articles. Articles covering different angles of a broad topic (e.g., "AI")
are NOT duplicates — only exact same news event/announcement.

Articles:
{json.dumps(titles, indent=2)}

Return format: [[0, 3, 7], [12, 15]] — just the JSON array, no explanation."""

    try:
        raw = client.complete(prompt, max_tokens=1000)
        start = raw.find("[")
        end = raw.rfind("]") + 1
        groups = json.loads(raw[start:end]) if start >= 0 else []
    except Exception as e:
        logger.warning(f"Deduplication LLM call failed: {e}. Skipping dedup.")
        return articles

    merged_indices = set()
    merged_articles = []

    for group in groups:
        if not group or len(group) < 2:
            continue
        primary_idx = group[0]
        primary = dict(articles[primary_idx])
        primary["all_sources"] = [
            {
                "label": articles[i].get("source_label", articles[i]["source"]),
                "url": articles[i]["url"],
                "is_nyt": articles[i].get("is_nyt", False),
            }
            for i in group
        ]
        if any(articles[i].get("is_nyt") for i in group):
            primary["is_nyt"] = True
        merged_articles.append(primary)
        for i in group:
            merged_indices.add(i)

    result = [a for i, a in enumerate(articles) if i not in merged_indices]
    result.extend(merged_articles)
    logger.info(
        f"Deduplication: {len(articles)} → {len(result)} articles ({len(merged_articles)} merges)"
    )
    return result


def score_articles(
    articles: list[dict], client: LLMClient, preferences: dict
) -> list[dict]:
    """Score each article, apply preference weights, return top MAX_ITEMS."""

    topic_weights = preferences.get("topic_weights", {})

    override_items = [a for a in articles if "score_override" in a]
    to_score = [a for a in articles if "score_override" not in a]

    max_candidates = int(os.environ.get("MAX_SCORE_CANDIDATES", 120))
    random.shuffle(to_score)
    to_score = to_score[:max_candidates]

    if client.name == "none":
        scored = _score_heuristic(to_score)
    else:
        topics = load_topics()
        batch_size = 30
        scored = []
        for i in range(0, len(to_score), batch_size):
            scored.extend(_score_batch(to_score[i : i + batch_size], client, topics))

    for a in scored:
        topic = a.get("topic_hint") or a.get("ai_topic", "")
        weight = topic_weights.get(topic, 1.0)
        a["final_score"] = min(100, a.get("claude_score", 50) * weight)

    for a in override_items:
        a["final_score"] = a["score_override"]
        a["claude_score"] = a["score_override"]

    all_scored = scored + override_items
    all_scored.sort(key=lambda x: x.get("final_score", 0), reverse=True)

    filtered = [a for a in all_scored if a.get("final_score", 0) >= MIN_SCORE]

    podcast_count = 0
    final = []
    for a in filtered:
        if a.get("is_podcast"):
            if podcast_count >= MAX_PODCAST_ITEMS:
                continue
            podcast_count += 1
        final.append(a)
        if len(final) >= MAX_ITEMS:
            break

    logger.info(
        f"Scoring: {len(articles)} candidates → {len(final)} selected (provider: {client.name})"
    )
    return final


def _score_heuristic(articles: list[dict]) -> list[dict]:
    """Assign scores without an LLM using source reputation and recency."""
    import datetime

    now = datetime.datetime.now(datetime.timezone.utc)

    for a in articles:
        source = a.get("source", "")
        base = _SOURCE_BASE_SCORES.get(source, 55)

        # Recency bonus: up to +10 for articles published within 12 hours
        published = a.get("published", "")
        try:
            pub_dt = datetime.datetime.fromisoformat(published.replace("Z", "+00:00"))
            age_hours = (now - pub_dt).total_seconds() / 3600
            recency_bonus = max(0, 10 - age_hours)
        except Exception:
            recency_bonus = 0

        # Reddit score signal (normalized, up to +15)
        reddit_bonus = 0
        if source == "Reddit":
            reddit_score = a.get("reddit_score", 0)
            reddit_bonus = min(15, reddit_score / 200 * 15)

        a["claude_score"] = min(100, base + recency_bonus + reddit_bonus)
        a["ai_topic"] = a.get("topic_hint", "")

    return articles


def _weight_label(weight: float) -> str:
    if weight >= 1.4:
        return "very high"
    if weight >= 1.2:
        return "high"
    if weight >= 1.1:
        return "medium-high"
    if weight >= 1.0:
        return "medium"
    return "low"


def _score_batch(articles: list[dict], client: LLMClient, topics: list[dict]) -> list[dict]:
    if not articles:
        return []

    compact = [
        {
            "idx": i,
            "title": a["title"],
            "source": a.get("source_label", a["source"]),
            "summary": (a.get("summary", "") or "")[:200],
            "topic_hint": a.get("topic_hint", ""),
        }
        for i, a in enumerate(articles)
    ]

    topic_lines = "\n".join(
        f"- {t['label']} (weight: {_weight_label(t.get('weight', 1.0))})"
        for t in topics
    )
    topic_ids = ", ".join(t["id"] for t in topics)
    topic_list = f"Topics of interest (score higher for these):\n{topic_lines}"

    prompt = f"""You are a news curation AI for the digest owner. Score each article 0-100.

Scoring criteria:
- Relevance (0-40): How well does it match the reader's interest topics?
- Novelty (0-30): Is this genuinely new, surprising, or non-obvious? Penalize "everyone covered this" stories.
- Intrinsic interest (0-30): Is this the kind of thing a curious, intelligent person would want to follow up on?

{topic_list}

For each article, also identify the best-matching topic from:
{topic_ids}

Articles to score:
{json.dumps(compact, indent=2)}

Return ONLY a JSON array in this format (no explanation):
[{{"idx": 0, "score": 72, "topic": "ai_coding"}}, ...]"""

    try:
        raw = client.complete(prompt, max_tokens=2000)
        start = raw.find("[")
        end = raw.rfind("]") + 1
        scores = json.loads(raw[start:end]) if start >= 0 else []

        score_map = {s["idx"]: s for s in scores}
        for i, a in enumerate(articles):
            s = score_map.get(i, {})
            a["claude_score"] = s.get("score", 50)
            a["ai_topic"] = s.get("topic", a.get("topic_hint", ""))

    except Exception as e:
        logger.warning(f"Scoring batch failed: {e}. Using default scores.")
        for a in articles:
            a["claude_score"] = 50
            a["ai_topic"] = a.get("topic_hint", "")

    return articles


def select_top(articles: list[dict]) -> list[dict]:
    """Main entry point: load LLM client, deduplicate, score, and select top articles."""
    client = load_llm_client()
    preferences = load_preferences()

    deduped = deduplicate(articles, client)
    selected = score_articles(deduped, client, preferences)
    return selected


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)
    data = json.load(sys.stdin)
    result = select_top(data)
    print(json.dumps(result, indent=2, default=str))
