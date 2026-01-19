"""
In-memory cache for parsed steps.

Caches ParsedPrepStep results to avoid redundant LLM calls for the same steps.
"""

import hashlib
import logging
import time
from dataclasses import dataclass
from typing import Dict, Optional

from backend.config import settings
from backend.engine.parsing.models import ParsedPrepStep

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """A cached parsed step with expiration time."""

    parsed_step: ParsedPrepStep
    expires_at: float  # Unix timestamp


class StepParsingCache:
    """
    In-memory cache for parsed recipe steps.

    Keys are generated from the hash of recipe_id + step_text.
    Entries expire after the configured TTL (default: 24 hours).

    Note: This is a simple in-memory cache. For multi-worker deployments,
    consider upgrading to Redis.
    """

    def __init__(self, ttl_hours: Optional[int] = None):
        """
        Initialize the cache.

        Args:
            ttl_hours: Time-to-live in hours. Defaults to config setting.
        """
        self._cache: Dict[str, CacheEntry] = {}
        self._ttl_seconds = (
            ttl_hours or settings.step_parsing_cache_ttl_hours
        ) * 3600

    def _generate_key(self, recipe_id: str, step_text: str) -> str:
        """Generate a cache key from recipe ID and step text."""
        content = f"{recipe_id}:{step_text}"
        return hashlib.sha256(content.encode()).hexdigest()[:32]

    def get(self, recipe_id: str, step_text: str) -> Optional[ParsedPrepStep]:
        """
        Get a cached parsed step if available and not expired.

        Args:
            recipe_id: The recipe identifier.
            step_text: The raw step text.

        Returns:
            The cached ParsedPrepStep or None if not found/expired.
        """
        key = self._generate_key(recipe_id, step_text)
        entry = self._cache.get(key)

        if entry is None:
            return None

        if time.time() > entry.expires_at:
            # Entry expired, remove it
            del self._cache[key]
            return None

        logger.debug(f"Cache hit for step: {step_text[:50]}...")
        return entry.parsed_step

    def set(self, recipe_id: str, step_text: str, parsed_step: ParsedPrepStep) -> None:
        """
        Cache a parsed step.

        Args:
            recipe_id: The recipe identifier.
            step_text: The raw step text.
            parsed_step: The parsed step to cache.
        """
        key = self._generate_key(recipe_id, step_text)
        expires_at = time.time() + self._ttl_seconds

        self._cache[key] = CacheEntry(
            parsed_step=parsed_step,
            expires_at=expires_at,
        )
        logger.debug(f"Cached step: {step_text[:50]}...")

    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()
        logger.info("Step parsing cache cleared")

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries from the cache.

        Returns:
            Number of entries removed.
        """
        now = time.time()
        expired_keys = [
            key for key, entry in self._cache.items() if now > entry.expires_at
        ]

        for key in expired_keys:
            del self._cache[key]

        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

        return len(expired_keys)

    @property
    def size(self) -> int:
        """Return the number of entries in the cache."""
        return len(self._cache)


# Global cache instance
_step_cache: Optional[StepParsingCache] = None


def get_step_cache() -> StepParsingCache:
    """Get or create the global step parsing cache."""
    global _step_cache
    if _step_cache is None:
        _step_cache = StepParsingCache()
    return _step_cache
