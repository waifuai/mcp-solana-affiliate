"""Simple in-memory caching for performance optimization."""

import time
from typing import Any, Dict, Optional
from threading import Lock
import logging

logger = logging.getLogger(__name__)

class SimpleCache:
    """Simple thread-safe in-memory cache with TTL support."""

    def __init__(self, default_ttl: int = 300):
        """Initialize cache with default TTL in seconds."""
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = Lock()
        self.default_ttl = default_ttl

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if it exists and hasn't expired."""
        with self._lock:
            if key not in self._cache:
                return None

            item = self._cache[key]
            if time.time() > item['expires_at']:
                # Item has expired, remove it
                del self._cache[key]
                return None

            logger.debug(f"Cache hit for key: {key}")
            return item['value']

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with optional TTL."""
        expires_at = time.time() + (ttl or self.default_ttl)

        with self._lock:
            self._cache[key] = {
                'value': value,
                'expires_at': expires_at,
                'created_at': time.time()
            }
            logger.debug(f"Cache set for key: {key}, expires at: {expires_at}")

    def delete(self, key: str) -> bool:
        """Delete item from cache."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"Cache deleted for key: {key}")
                return True
            return False

    def clear(self) -> None:
        """Clear all items from cache."""
        with self._lock:
            cleared_count = len(self._cache)
            self._cache.clear()
            logger.info(f"Cache cleared, {cleared_count} items removed")

    def cleanup(self) -> int:
        """Remove expired items from cache."""
        with self._lock:
            current_time = time.time()
            expired_keys = [
                key for key, item in self._cache.items()
                if current_time > item['expires_at']
            ]

            for key in expired_keys:
                del self._cache[key]

            if expired_keys:
                logger.info(f"Cache cleanup removed {len(expired_keys)} expired items")

            return len(expired_keys)

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            current_time = time.time()
            total_items = len(self._cache)
            expired_items = sum(
                1 for item in self._cache.values()
                if current_time > item['expires_at']
            )

            return {
                'total_items': total_items,
                'expired_items': expired_items,
                'active_items': total_items - expired_items,
                'hit_count': getattr(self, '_hit_count', 0),
                'miss_count': getattr(self, '_miss_count', 0)
            }

# Global cache instances
affiliate_cache = SimpleCache(default_ttl=300)  # 5 minutes for affiliate data
metrics_cache = SimpleCache(default_ttl=60)     # 1 minute for metrics
health_cache = SimpleCache(default_ttl=30)      # 30 seconds for health data

def get_affiliate_cache_key(affiliate_id: str) -> str:
    """Generate cache key for affiliate data."""
    return f"affiliate:{affiliate_id}"

def get_metrics_cache_key() -> str:
    """Generate cache key for metrics."""
    return "metrics:all"

def get_health_cache_key() -> str:
    """Generate cache key for health data."""
    return "health:status"