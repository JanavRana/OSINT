"""
Rate limiter for plugin execution.

Enforces per-plugin rate limits to prevent overwhelming external platforms
and respect their rate limit policies.
"""

import asyncio
import logging
import time
from collections import deque
from typing import Optional

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter for plugin requests.
    
    Supports:
    - Per-plugin rate limiting
    - Configurable requests per minute
    - Burst allowance
    - Async/await integration
    """
    
    def __init__(self):
        # Per-plugin state
        self._tokens: dict[str, float] = {}
        self._last_refill: dict[str, float] = {}
        self._max_tokens: dict[str, float] = {}
        self._refill_rate: dict[str, float] = {}  # tokens per second
        self._locks: dict[str, asyncio.Lock] = {}
        
        # Request tracking
        self._request_times: dict[str, deque] = {}
    
    def configure(
        self,
        plugin_id: str,
        requests_per_minute: int,
        burst_size: Optional[int] = None
    ) -> None:
        """
        Configure rate limit for a plugin.
        
        Args:
            plugin_id: Plugin identifier
            requests_per_minute: Maximum requests per minute
            burst_size: Burst allowance (defaults to requests_per_minute)
        """
        if requests_per_minute <= 0:
            raise ValueError("requests_per_minute must be positive")
        
        burst = burst_size if burst_size is not None else requests_per_minute
        
        self._max_tokens[plugin_id] = float(burst)
        self._tokens[plugin_id] = float(burst)  # Start with full bucket
        self._refill_rate[plugin_id] = requests_per_minute / 60.0  # tokens per second
        self._last_refill[plugin_id] = time.monotonic()
        self._locks[plugin_id] = asyncio.Lock()
        self._request_times[plugin_id] = deque(maxlen=requests_per_minute * 2)
        
        logger.debug(
            f"Configured rate limiter for {plugin_id}: "
            f"{requests_per_minute} req/min, burst={burst}"
        )
    
    def _refill_tokens(self, plugin_id: str) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        last = self._last_refill.get(plugin_id, now)
        elapsed = now - last
        
        if elapsed > 0:
            refill_amount = elapsed * self._refill_rate[plugin_id]
            self._tokens[plugin_id] = min(
                self._max_tokens[plugin_id],
                self._tokens[plugin_id] + refill_amount
            )
            self._last_refill[plugin_id] = now
    
    async def acquire(self, plugin_id: str, tokens: float = 1.0) -> None:
        """
        Acquire tokens for a request.
        
        Blocks until tokens are available.
        
        Args:
            plugin_id: Plugin identifier
            tokens: Number of tokens to acquire (default 1)
        """
        if plugin_id not in self._locks:
            # Plugin not configured, allow through
            logger.warning(f"Rate limiter not configured for {plugin_id}, allowing request")
            return
        
        async with self._locks[plugin_id]:
            while True:
                self._refill_tokens(plugin_id)
                
                if self._tokens[plugin_id] >= tokens:
                    self._tokens[plugin_id] -= tokens
                    self._request_times[plugin_id].append(time.monotonic())
                    return
                
                # Calculate wait time
                tokens_needed = tokens - self._tokens[plugin_id]
                wait_time = tokens_needed / self._refill_rate[plugin_id]
                
                logger.debug(
                    f"Rate limit reached for {plugin_id}, "
                    f"waiting {wait_time:.2f}s for {tokens_needed:.2f} tokens"
                )
                
                await asyncio.sleep(wait_time)
    
    def try_acquire(self, plugin_id: str, tokens: float = 1.0) -> bool:
        """
        Try to acquire tokens without blocking.
        
        Args:
            plugin_id: Plugin identifier
            tokens: Number of tokens to acquire
            
        Returns:
            True if tokens were acquired, False otherwise
        """
        if plugin_id not in self._locks:
            return True
        
        self._refill_tokens(plugin_id)
        
        if self._tokens[plugin_id] >= tokens:
            self._tokens[plugin_id] -= tokens
            self._request_times[plugin_id].append(time.monotonic())
            return True
        
        return False
    
    def get_available_tokens(self, plugin_id: str) -> float:
        """Get number of available tokens for a plugin."""
        if plugin_id not in self._tokens:
            return float('inf')
        
        self._refill_tokens(plugin_id)
        return self._tokens[plugin_id]
    
    def get_wait_time(self, plugin_id: str, tokens: float = 1.0) -> float:
        """
        Calculate wait time for tokens to become available.
        
        Args:
            plugin_id: Plugin identifier
            tokens: Number of tokens needed
            
        Returns:
            Wait time in seconds (0 if immediately available)
        """
        if plugin_id not in self._refill_rate:
            return 0.0
        
        self._refill_tokens(plugin_id)
        available = self._tokens[plugin_id]
        
        if available >= tokens:
            return 0.0
        
        tokens_needed = tokens - available
        return tokens_needed / self._refill_rate[plugin_id]
    
    def get_request_rate(self, plugin_id: str, window_seconds: int = 60) -> float:
        """
        Calculate current request rate for a plugin.
        
        Args:
            plugin_id: Plugin identifier
            window_seconds: Time window to measure (default 60s)
            
        Returns:
            Requests per minute in the window
        """
        if plugin_id not in self._request_times:
            return 0.0
        
        now = time.monotonic()
        cutoff = now - window_seconds
        
        # Count requests in window
        request_times = self._request_times[plugin_id]
        recent_requests = sum(1 for t in request_times if t >= cutoff)
        
        # Convert to per-minute rate
        return (recent_requests / window_seconds) * 60.0
    
    def get_statistics(self, plugin_id: str) -> dict:
        """Get rate limiter statistics for a plugin."""
        if plugin_id not in self._tokens:
            return {"configured": False}
        
        self._refill_tokens(plugin_id)
        
        return {
            "configured": True,
            "available_tokens": self._tokens[plugin_id],
            "max_tokens": self._max_tokens[plugin_id],
            "refill_rate_per_second": self._refill_rate[plugin_id],
            "current_rate_per_minute": self.get_request_rate(plugin_id),
            "total_requests": len(self._request_times[plugin_id]),
        }
    
    def reset(self, plugin_id: str) -> None:
        """Reset rate limiter state for a plugin."""
        if plugin_id in self._tokens:
            self._tokens[plugin_id] = self._max_tokens[plugin_id]
            self._last_refill[plugin_id] = time.monotonic()
            self._request_times[plugin_id].clear()
            logger.info(f"Reset rate limiter for {plugin_id}")
    
    def clear(self) -> None:
        """Clear all rate limiter state."""
        self._tokens.clear()
        self._last_refill.clear()
        self._max_tokens.clear()
        self._refill_rate.clear()
        self._locks.clear()
        self._request_times.clear()


# Global singleton instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


def reset_rate_limiter() -> None:
    """Reset the global rate limiter. Mainly for testing."""
    global _rate_limiter
    if _rate_limiter:
        _rate_limiter.clear()
    _rate_limiter = None
