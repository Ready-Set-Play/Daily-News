"""
llm/openai.py — OpenAI provider.

Requires: pip install openai>=1.0.0
"""

import os

from .base import LLMClient

DEFAULT_MODEL = "gpt-4o-mini"


class OpenAIClient(LLMClient):
    name = "openai"

    def __init__(self, api_key: str | None = None, model: str | None = None):
        try:
            import openai
        except ImportError:
            raise ImportError(
                "openai package is required for LLM_PROVIDER=openai. "
                "Run: pip install openai>=1.0.0"
            )
        self._client = openai.OpenAI(
            api_key=api_key or os.environ.get("OPENAI_API_KEY", "")
        )
        self.model = model or os.environ.get("LLM_MODEL", DEFAULT_MODEL)

    def complete(self, prompt: str, max_tokens: int = 2000) -> str:
        response = self._client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content.strip()
