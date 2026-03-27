"""
llm/base.py — Abstract LLM client interface.

All provider implementations must subclass LLMClient and implement complete().
"""

from abc import ABC, abstractmethod


class LLMClient(ABC):
    """Minimal interface for an LLM provider."""

    name: str = ""

    @abstractmethod
    def complete(self, prompt: str, max_tokens: int = 2000) -> str:
        """Send a prompt and return the response text."""
        ...
