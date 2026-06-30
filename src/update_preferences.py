"""
update_preferences.py — Recalculate topic interest weights from feedback history.
Run weekly via GitHub Actions. Updates config/preferences.json in place.
"""

import json
import os
from datetime import datetime, timezone, timedelta
from collections import defaultdict

CONFIG_DIR = os.path.join(os.path.dirname(__file__), "..", "config")
FEEDBACK_DIR = os.path.join(os.path.dirname(__file__), "..", "feedback")
FEEDBACK_FILE = os.path.join(FEEDBACK_DIR, "history.jsonl")
PREFS_FILE = os.path.join(CONFIG_DIR, "preferences.json")

LOOKBACK_DAYS = 90
MIN_WEIGHT = 0.5
MAX_WEIGHT = 2.0
BASE_WEIGHT = 1.0


def load_feedback(lookback_days: int) -> list[dict]:
    if not os.path.exists(FEEDBACK_FILE):
        return []

    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=lookback_days)
    entries = []

    with open(FEEDBACK_FILE) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                ts = datetime.fromisoformat(entry.get("timestamp", "2000-01-01"))
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                if ts >= cutoff:
                    entries.append(entry)
            except Exception:
                continue

    return entries


def calculate_weights(feedback: list[dict]) -> dict[str, float]:
    """
    Calculate per-topic weights using a simple Bayesian-ish score:
    weight = base + adjustment based on (ups - downs) / (ups + downs + smoothing)
    Result clamped to [MIN_WEIGHT, MAX_WEIGHT].
    """
    topic_counts: dict[str, dict[str, int]] = defaultdict(lambda: {"up": 0, "down": 0})

    for entry in feedback:
        topic = entry.get("topic", "")
        direction = entry.get("direction", "")
        if topic and direction in ("up", "down"):
            topic_counts[topic][direction] += 1

    weights = {}
    for topic, counts in topic_counts.items():
        ups = counts["up"]
        downs = counts["down"]
        total = ups + downs
        smoothing = 5  # Requires some signal before strong adjustment

        # Wilson-score-inspired: net positive ratio adjusted for sample size
        net_ratio = (ups - downs) / (total + smoothing)
        # Map net_ratio (-1 to 1) to weight adjustment (-0.5 to +1.0)
        adjustment = net_ratio * 0.75
        weight = BASE_WEIGHT + adjustment
        weights[topic] = round(max(MIN_WEIGHT, min(MAX_WEIGHT, weight)), 3)

    return weights


def update_preferences():
    # Load current preferences
    with open(PREFS_FILE) as f:
        prefs = json.load(f)

    current_weights = prefs.get("topic_weights", {})
    feedback = load_feedback(LOOKBACK_DAYS)

    print(f"Loaded {len(feedback)} feedback entries from last {LOOKBACK_DAYS} days")

    if not feedback:
        print("No feedback yet. Preferences unchanged.")
        return

    new_weights = calculate_weights(feedback)

    # Merge: only update topics that have feedback signal
    updated = dict(current_weights)
    for topic, weight in new_weights.items():
        updated[topic] = weight
        print(
            f"  {topic}: {current_weights.get(topic, BASE_WEIGHT):.2f} → {weight:.2f}"
        )

    # Update feedback counts in preferences
    counts: dict[str, dict[str, int]] = defaultdict(lambda: {"up": 0, "down": 0})
    for entry in feedback:
        topic = entry.get("topic", "")
        direction = entry.get("direction", "")
        if topic and direction in ("up", "down"):
            counts[topic][direction] += 1

    prefs["topic_weights"] = updated
    prefs["feedback_counts"] = {t: dict(c) for t, c in counts.items()}
    prefs["_meta"]["last_updated"] = datetime.now(tz=timezone.utc).date().isoformat()

    with open(PREFS_FILE, "w") as f:
        json.dump(prefs, f, indent=2)

    print(f"Updated preferences.json with {len(new_weights)} topic adjustments")


if __name__ == "__main__":
    update_preferences()
