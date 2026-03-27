"""
base.py — BaseSource ABC and SourceFetchError for the plugin system.
All source plugins must inherit from BaseSource.
"""

import os
from abc import ABC, abstractmethod


class SourceFetchError(Exception):
    """Raised by a plugin when fetch fails in a non-recoverable way.
    The pipeline will catch this, log a warning, and skip the source."""

    pass


class BaseSource(ABC):
    """
    Contract all source plugins must fulfill.

    Constructor receives two dicts from sources.yaml:
      config — source-specific settings (sections, queries, feeds, etc.)
      auth   — credential config (api_key_env, etc.)

    Implement fetch() to return a list of article dicts.
    """

    name: str = ""  # e.g., "nyt", "hackernews"
    requires_auth: bool = False

    def __init__(self, config: dict, auth: dict):
        self.config = config
        self.auth = auth

    @abstractmethod
    def fetch(self) -> list[dict]:
        """
        Fetch articles from this source.

        Returns a list of dicts. Each dict MUST contain:
          id, title, url, source, source_label, summary,
          published, topic_hint, image_url

        Raise SourceFetchError on unrecoverable failure.
        The pipeline will skip this source and continue with others.
        """
        ...

    def is_configured(self) -> bool:
        """Return False if required credentials are missing.
        Override in plugins that require auth."""
        if self.requires_auth:
            env_var = self.auth.get("api_key_env", "")
            return bool(os.environ.get(env_var, ""))
        return True
