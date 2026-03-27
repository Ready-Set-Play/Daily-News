"""
sources/__init__.py — Plugin loader for the source plugin system.
"""

import importlib
import logging

from .base import BaseSource, SourceFetchError

logger = logging.getLogger(__name__)


def load_sources(config: list[dict]) -> list[BaseSource]:
    """Dynamically import and instantiate enabled source plugins.

    Each entry in config must have:
      plugin: <module name in src/sources/>
      enabled: true/false
      config: <dict passed to Source.__init__>   (optional)
      auth:   <dict passed to Source.__init__>   (optional)
    """
    sources = []
    for entry in config:
        if not entry.get("enabled", True):
            continue
        plugin_name = entry["plugin"]
        try:
            module = importlib.import_module(f"sources.{plugin_name}")
            cls = getattr(module, "Source")
            instance = cls(entry.get("config", {}), entry.get("auth", {}))
            if not instance.is_configured():
                logger.warning(
                    f"Source plugin '{plugin_name}' is missing credentials "
                    f"({instance.auth.get('api_key_env', '?')} not set) — skipping"
                )
                continue
            sources.append(instance)
        except (ImportError, AttributeError) as e:
            logger.error(f"Failed to load source plugin '{plugin_name}': {e}")
    return sources


__all__ = ["BaseSource", "SourceFetchError", "load_sources"]
