"""
Response cache for plugin results.

Caches successful plugin results with configurable TTL to reduce
redundant requests across investigations.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """A cached value with metadata."""
    key: str
    value: Any
    timestamp: float
    ttl_seconds: float
    hit_count: int = 0
    
    def is_expired(self) -> bool:
        """Check if entry has expired."""
        return time.monotonic() - self.timestamp > self.ttl_seconds
    
    def age_seconds(self) -> float:
        """Get age of entry in seconds."""
        return time.monotonic() - self.timestamp


class Cache:
    """
    TTL-based cache for plugin results.
    
    Features:
    - Per-plugin TTL configuration
    - Automatic expiration
    - Hit/miss statistics
    - Size limits with LRU eviction
    """
    
    def __init__(self, max_size: int = 10000, default_ttl: int = 3600):
        """
        Initialize cache.
        
        Args:
            max_size: Maximum number of entries
            default_ttl: Default TTL in seconds (1 hour)
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        
        self._cache: dict[str, CacheEntry] = {}
        self._plugin_ttls: dict[str, int] = {}
        self._lock = asyncio.Lock()
        
        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0
    
    def configure_plugin_ttl(self, plugin_id: str, ttl_seconds: int) -> None:
        """
        Configure TTL for a specific plugin.
        
        Args:
            plugin_id: Plugin identifier
            ttl_seconds: TTL in seconds
        """
        self._plugin_ttls[plugin_id] = ttl_seconds
        logger.debug(f"Configured cache TTL for {plugin_id}: {ttl_seconds}s")
    
    def _get_ttl(self, plugin_id: str) -> int:
        """Get TTL for a plugin."""
        return self._plugin_ttls.get(plugin_id, self.default_ttl)
    
    def _make_key(self, plugin_id: str, identifier: str) -> str:
        """Create cache key."""
        return f"{plugin_id}:{identifier}"
    
    def _evict_expired(self) -> int:
        """Remove expired entries. Returns number evicted."""
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired()
        ]
        
        for key in expired_keys:
            del self._cache[key]
        
        if expired_keys:
            logger.debug(f"Evicted {len(expired_keys)} expired cache entries")
        
        return len(expired_keys)
    
    def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if not self._cache:
            return
        
        # Find entry with oldest timestamp and lowest hit count
        lru_key = min(
            self._cache.keys(),
            key=lambda k: (self._cache[k].hit_count, self._cache[k].timestamp)
        )
        
        del self._cache[lru_key]
        self._evictions += 1
        logger.debug(f"Evicted LRU cache entry: {lru_key}")
    
    async def get(self, plugin_id: str, identifier: str) -> Optional[Any]:
        """
        Get cached value.
        
        Args:
            plugin_id: Plugin identifier
            identifier: Identifier value (username, email, phone)
            
        Returns:
            Cached value if found and not expired, None otherwise
        """
        key = self._make_key(plugin_id, identifier)
        
        async with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                self._misses += 1
                return None
            
            if entry.is_expired():
                del self._cache[key]
                self._misses += 1
                return None
            
            # Cache hit
            entry.hit_count += 1
            self._hits += 1
            
            logger.debug(
                f"Cache hit: {key} (age={entry.age_seconds():.1f}s, hits={entry.hit_count})"
            )
            
            return entry.value
    
    async def set(self, plugin_id: str, identifier: str, value: Any) -> None:
        """
        Store value in cache.
        
        Args:
            plugin_id: Plugin identifier
            identifier: Identifier value
            value: Value to cache
        """
        key = self._make_key(plugin_id, identifier)
        ttl = self._get_ttl(plugin_id)
        
        async with self._lock:
            # Evict expired entries periodically
            if len(self._cache) % 100 == 0:
                self._evict_expired()
            
            # Evict LRU if at capacity
            if len(self._cache) >= self.max_size:
                self._evict_lru()
            
            entry = CacheEntry(
                key=key,
                value=value,
                timestamp=time.monotonic(),
                ttl_seconds=float(ttl)
            )
            
            self._cache[key] = entry
            
            logger.debug(f"Cache set: {key} (ttl={ttl}s)")
    
    async def delete(self, plugin_id: str, identifier: str) -> bool:
        """
        Delete cached value.
        
        Args:
            plugin_id: Plugin identifier
            identifier: Identifier value
            
        Returns:
            True if entry was deleted, False if not found
        """
        key = self._make_key(plugin_id, identifier)
        
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"Cache delete: {key}")
                return True
            return False
    
    async def clear_plugin(self, plugin_id: str) -> int:
        """
        Clear all cached entries for a plugin.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            Number of entries cleared
        """
        prefix = f"{plugin_id}:"
        
        async with self._lock:
            keys_to_delete = [
                key for key in self._cache.keys()
                if key.startswith(prefix)
            ]
            
            for key in keys_to_delete:
                del self._cache[key]
            
            logger.info(f"Cleared {len(keys_to_delete)} cache entries for {plugin_id}")
            
            return len(keys_to_delete)
    
    async def clear(self) -> None:
        """Clear all cache entries."""
        async with self._lock:
            count = len(self._cache)
            self._cache.clear()
            logger.info(f"Cleared all {count} cache entries")
    
    def get_statistics(self) -> dict:
        """Get cache statistics."""
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0.0
        
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate_percent": hit_rate,
            "evictions": self._evictions,
        }
    
    def get_plugin_statistics(self, plugin_id: str) -> dict:
        """Get statistics for a specific plugin."""
        prefix = f"{plugin_id}:"
        
        entries = [
            entry for key, entry in self._cache.items()
            if key.startswith(prefix)
        ]
        
        if not entries:
            return {
                "plugin_id": plugin_id,
                "entries": 0,
                "ttl_seconds": self._get_ttl(plugin_id),
            }
        
        total_hits = sum(e.hit_count for e in entries)
        avg_age = sum(e.age_seconds() for e in entries) / len(entries)
        
        return {
            "plugin_id": plugin_id,
            "entries": len(entries),
            "ttl_seconds": self._get_ttl(plugin_id),
            "total_hits": total_hits,
            "average_age_seconds": avg_age,
        }


# Global singleton instance
_cache: Optional[Cache] = None


def get_cache() -> Cache:
    """Get the global cache instance."""
    global _cache
    if _cache is None:
        _cache = Cache()
    return _cache


def reset_cache() -> None:
    """Reset the global cache. Mainly for testing."""
    global _cache
    _cache = None
