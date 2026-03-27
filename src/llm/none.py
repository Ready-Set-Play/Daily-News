"""
llm/none.py — Heuristic fallback when no LLM provider is configured.

Deduplication is skipped. Scoring uses source reputation + recency.
Summarization truncates the existing summary field to 60 words.
No API calls, no cost.
"""

from .base import LLMClient


class NoopClient(LLMClient):
    """
    Satisfies the LLMClient interface but raises NotImplementedError on complete().
    score.py and summarize.py special-case this provider to skip LLM calls entirely.
    """

    name = "none"

    def complete(self, prompt: str, max_tokens: int = 2000) -> str:
        raise NotImplementedError("NoopClient does not make LLM calls.")
