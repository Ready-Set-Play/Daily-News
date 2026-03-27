"""
llm/anthropic.py — Anthropic Claude provider.
"""

import os

import anthropic as _anthropic

from .base import LLMClient

DEFAULT_MODEL = "claude-haiku-4-5-20251001"


class AnthropicClient(LLMClient):
    name = "anthropic"

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self._client = _anthropic.Anthropic(
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        )
        self.model = model or os.environ.get("LLM_MODEL", DEFAULT_MODEL)

    def complete(self, prompt: str, max_tokens: int = 2000) -> str:
        response = self._client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
