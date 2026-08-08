"""
Circuit breaker for plugin execution.

Prevents wasting resources on failing plugins by temporarily disabling
them after repeated failures.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from ..types import CircuitBreakerState

logger = logging.getLogger(__name__)


@dataclass
class CircuitBreakerConfig:
    """Configuration for a circuit breaker."""
    failure_threshold: int = 5
    success_threshold: int = 2
    timeout_seconds: int = 60
    half_open_max_calls: int = 1


@dataclass
class CircuitBreakerStats:
    """Statistics for a circuit breaker."""
    state: CircuitBreakerState
    failure_count: int = 0
    success_count: int = 0
    opened_at: Optional[float] = None
    last_failure_at: Optional[float] = None
    last_success_at: Optional[float] = None
    total_calls: int = 0
    total_failures: int = 0
    total_successes: int = 0
    state_changes: list[tuple[CircuitBreakerState, float]] = field(default_factory=list)


class CircuitBreaker:
    """
    Circuit breaker for a single plugin.
    
    States:
    - CLOSED: Normal operation, requests allowed
    - OPEN: Too many failures, requests blocked
    - HALF_OPEN: Testing if service recovered, limited requests allowed
    """
    
    def __init__(
        self,
        plugin_id: str,
        config: Optional[CircuitBreakerConfig] = None
    ):
        """
        Initialize circuit breaker.
        
        Args:
            plugin_id: Plugin identifier
            config: Circuit breaker configuration
        """
        self.plugin_id = plugin_id
        self.config = config or CircuitBreakerConfig()
        
        self._state = CircuitBreakerState.CLOSED
        self._stats = CircuitBreakerStats(state=CircuitBreakerState.CLOSED)
        self._lock = asyncio.Lock()
        
        logger.debug(f"Initialized circuit breaker for {plugin_id}")
    
    @property
    def state(self) -> CircuitBreakerState:
        """Get current state."""
        return self._state
    
    def _transition_to(self, new_state: CircuitBreakerState) -> None:
        """Transition to a new state."""
        if new_state == self._state:
            return
        
        old_state = self._state
        self._state = new_state
        self._stats.state = new_state
        
        now = time.monotonic()
        self._stats.state_changes.append((new_state, now))
        
        if new_state == CircuitBreakerState.OPEN:
            self._stats.opened_at = now
        
        logger.info(
            f"Circuit breaker {self.plugin_id} transitioned: {old_state} -> {new_state}"
        )
    
    async def is_call_allowed(self) -> bool:
        """
        Check if a call is allowed.
        
        Returns:
            True if call is allowed, False if circuit is open
        """
        async with self._lock:
            if self._state == CircuitBreakerState.CLOSED:
                return True
            
            if self._state == CircuitBreakerState.OPEN:
                # Check if timeout has elapsed
                if self._stats.opened_at is not None:
                    elapsed = time.monotonic() - self._stats.opened_at
                    if elapsed >= self.config.timeout_seconds:
                        # Transition to half-open
                        self._transition_to(CircuitBreakerState.HALF_OPEN)
                        self._stats.success_count = 0
                        self._stats.failure_count = 0
                        return True
                return False
            
            if self._state == CircuitBreakerState.HALF_OPEN:
                # Allow limited calls in half-open state
                return self._stats.total_calls < self.config.half_open_max_calls
            
            return False
    
    async def record_success(self) -> None:
        """Record a successful call."""
        async with self._lock:
            self._stats.total_calls += 1
            self._stats.total_successes += 1
            self._stats.success_count += 1
            self._stats.last_success_at = time.monotonic()
            
            if self._state == CircuitBreakerState.HALF_OPEN:
                if self._stats.success_count >= self.config.success_threshold:
                    # Recovered, close the circuit
                    self._transition_to(CircuitBreakerState.CLOSED)
                    self._stats.failure_count = 0
                    self._stats.success_count = 0
            
            elif self._state == CircuitBreakerState.CLOSED:
                # Reset failure count on success
                self._stats.failure_count = 0
    
    async def record_failure(self) -> None:
        """Record a failed call."""
        async with self._lock:
            self._stats.total_calls += 1
            self._stats.total_failures += 1
            self._stats.failure_count += 1
            self._stats.last_failure_at = time.monotonic()
            
            if self._state == CircuitBreakerState.CLOSED:
                if self._stats.failure_count >= self.config.failure_threshold:
                    # Too many failures, open the circuit
                    self._transition_to(CircuitBreakerState.OPEN)
            
            elif self._state == CircuitBreakerState.HALF_OPEN:
                # Failed during recovery, reopen the circuit
                self._transition_to(CircuitBreakerState.OPEN)
                self._stats.failure_count = 0
                self._stats.success_count = 0
    
    def get_statistics(self) -> CircuitBreakerStats:
        """Get circuit breaker statistics."""
        return self._stats
    
    async def reset(self) -> None:
        """Reset circuit breaker to closed state."""
        async with self._lock:
            self._transition_to(CircuitBreakerState.CLOSED)
            self._stats.failure_count = 0
            self._stats.success_count = 0
            logger.info(f"Reset circuit breaker for {self.plugin_id}")


class CircuitBreakerRegistry:
    """
    Registry managing circuit breakers for all plugins.
    """
    
    def __init__(self, default_config: Optional[CircuitBreakerConfig] = None):
        """
        Initialize circuit breaker registry.
        
        Args:
            default_config: Default configuration for new circuit breakers
        """
        self.default_config = default_config or CircuitBreakerConfig()
        self._breakers: dict[str, CircuitBreaker] = {}
        self._configs: dict[str, CircuitBreakerConfig] = {}
        self._lock = asyncio.Lock()
    
    def configure(self, plugin_id: str, config: CircuitBreakerConfig) -> None:
        """Configure circuit breaker for a plugin."""
        self._configs[plugin_id] = config
        logger.debug(f"Configured circuit breaker for {plugin_id}")
    
    async def get_breaker(self, plugin_id: str) -> CircuitBreaker:
        """
        Get or create circuit breaker for a plugin.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            CircuitBreaker instance
        """
        if plugin_id not in self._breakers:
            async with self._lock:
                # Double-check after acquiring lock
                if plugin_id not in self._breakers:
                    config = self._configs.get(plugin_id, self.default_config)
                    self._breakers[plugin_id] = CircuitBreaker(plugin_id, config)
        
        return self._breakers[plugin_id]
    
    async def is_call_allowed(self, plugin_id: str) -> bool:
        """Check if a call is allowed for a plugin."""
        breaker = await self.get_breaker(plugin_id)
        return await breaker.is_call_allowed()
    
    async def record_success(self, plugin_id: str) -> None:
        """Record successful call for a plugin."""
        breaker = await self.get_breaker(plugin_id)
        await breaker.record_success()
    
    async def record_failure(self, plugin_id: str) -> None:
        """Record failed call for a plugin."""
        breaker = await self.get_breaker(plugin_id)
        await breaker.record_failure()
    
    async def get_state(self, plugin_id: str) -> CircuitBreakerState:
        """Get current state of a plugin's circuit breaker."""
        breaker = await self.get_breaker(plugin_id)
        return breaker.state
    
    async def get_statistics(self, plugin_id: str) -> CircuitBreakerStats:
        """Get statistics for a plugin's circuit breaker."""
        breaker = await self.get_breaker(plugin_id)
        return breaker.get_statistics()
    
    async def reset(self, plugin_id: str) -> None:
        """Reset circuit breaker for a plugin."""
        breaker = await self.get_breaker(plugin_id)
        await breaker.reset()
    
    async def reset_all(self) -> None:
        """Reset all circuit breakers."""
        for breaker in self._breakers.values():
            await breaker.reset()
        logger.info("Reset all circuit breakers")
    
    def get_all_states(self) -> dict[str, CircuitBreakerState]:
        """Get states of all circuit breakers."""
        return {
            plugin_id: breaker.state
            for plugin_id, breaker in self._breakers.items()
        }
    
    def get_summary(self) -> dict:
        """Get summary statistics for all circuit breakers."""
        summary = {
            "total": len(self._breakers),
            "by_state": {
                CircuitBreakerState.CLOSED: 0,
                CircuitBreakerState.OPEN: 0,
                CircuitBreakerState.HALF_OPEN: 0,
            }
        }
        
        for breaker in self._breakers.values():
            summary["by_state"][breaker.state] += 1
        
        return summary
    
    def clear(self) -> None:
        """Clear all circuit breakers. Mainly for testing."""
        self._breakers.clear()
        self._configs.clear()


# Global singleton instance
_circuit_breaker_registry: Optional[CircuitBreakerRegistry] = None


def get_circuit_breaker_registry() -> CircuitBreakerRegistry:
    """Get the global circuit breaker registry."""
    global _circuit_breaker_registry
    if _circuit_breaker_registry is None:
        _circuit_breaker_registry = CircuitBreakerRegistry()
    return _circuit_breaker_registry


def reset_circuit_breaker_registry() -> None:
    """Reset the global registry. Mainly for testing."""
    global _circuit_breaker_registry
    if _circuit_breaker_registry:
        _circuit_breaker_registry.clear()
    _circuit_breaker_registry = None
