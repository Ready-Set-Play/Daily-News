"""
llm/__init__.py — LLM provider factory.

Usage:
    from llm import load_llm_client
    client = load_llm_client()

Controlled by env vars:
    LLM_PROVIDER   anthropic (default) | openai | ollama | none
    LLM_MODEL      optional model override (provider-specific default used if unset)
"""

import os

from .base import LLMClient


def load_llm_client() -> LLMClient:
    provider = os.environ.get("LLM_PROVIDER", "anthropic").lower().strip()

    if provider == "anthropic":
        from .anthropic import AnthropicClient

        return AnthropicClient()

    if provider == "openai":
        from .openai import OpenAIClient

        return OpenAIClient()

    if provider == "ollama":
        from .ollama import OllamaClient

        return OllamaClient()

    if provider == "none":
        from .none import NoopClient

        return NoopClient()

    raise ValueError(
        f"Unknown LLM_PROVIDER '{provider}'. "
        "Valid options: anthropic, openai, ollama, none"
    )


__all__ = ["LLMClient", "load_llm_client"]
