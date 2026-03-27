"""
llm/ollama.py — Local Ollama provider.

Requires a running Ollama instance. No additional Python packages needed.
Default base URL: http://localhost:11434
Override with OLLAMA_BASE_URL env var.
"""

import json
import os
import urllib.request

from .base import LLMClient

DEFAULT_MODEL = "llama3.2"
DEFAULT_BASE_URL = "http://localhost:11434"


class OllamaClient(LLMClient):
    name = "ollama"

    def __init__(self, base_url: str | None = None, model: str | None = None):
        self.base_url = (
            base_url or os.environ.get("OLLAMA_BASE_URL", DEFAULT_BASE_URL)
        ).rstrip("/")
        self.model = model or os.environ.get("LLM_MODEL", DEFAULT_MODEL)

    def complete(self, prompt: str, max_tokens: int = 2000) -> str:
        payload = json.dumps(
            {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {"num_predict": max_tokens},
            }
        ).encode()

        req = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
        return data.get("response", "").strip()
