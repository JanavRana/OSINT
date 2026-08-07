"""
Tests for circuit breaker.
"""

import pytest
import asyncio

from app.identity.plugin_runtime.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerRegistry,
)
from app.identity.types import CircuitBreakerState


@pytest.fixture
def config():
    """Provide test configuration."""
    return CircuitBreakerConfig(
        failure_threshold=3,
        success_threshold=2,
        timeout_seconds=1,
        half_open_max_calls=1
    )


@pytest.mark.asyncio
async def test_circuit_breaker_starts_closed(config):
    """Test that circuit breaker starts in CLOSED state."""
    breaker = CircuitBreaker("test-plugin", config)
    
    assert breaker.state == CircuitBreakerState.CLOSED
    assert await breaker.is_call_allowed() is True


@pytest.mark.asyncio
async def test_circuit_breaker_opens_on_failures(config):
    """Test that circuit breaker opens after threshold failures."""
    breaker = CircuitBreaker("test-plugin", config)
    
    # Record failures up to threshold
    for _ in range(config.failure_threshold):
        await breaker.record_failure()
    
    # Should now be OPEN
    assert breaker.state == CircuitBreakerState.OPEN
    assert await breaker.is_call_allowed() is False


@pytest.mark.asyncio
async def test_circuit_breaker_resets_on_success(config):
    """Test that failures are reset on success."""
    breaker = CircuitBreaker("test-plugin", config)
    
    # Record some failures
    await breaker.record_failure()
    await breaker.record_failure()
    
    # Record success
    await breaker.record_success()
    
    # Should still be CLOSED and failure count reset
    assert breaker.state == CircuitBreakerState.CLOSED
    
    # Would need 3 more failures to open
    await breaker.record_failure()
    await breaker.record_failure()
    assert breaker.state == CircuitBreakerState.CLOSED


@pytest.mark.asyncio
async def test_circuit_breaker_transitions_to_half_open(config):
    """Test transition from OPEN to HALF_OPEN after timeout."""
    config.timeout_seconds = 0.1  # Short timeout for testing
    breaker = CircuitBreaker("test-plugin", config)
    
    # Open the circuit
    for _ in range(config.failure_threshold):
        await breaker.record_failure()
    
    assert breaker.state == CircuitBreakerState.OPEN
    
    # Wait for timeout
    await asyncio.sleep(0.2)
    
    # Should transition to HALF_OPEN
    assert await breaker.is_call_allowed() is True
    assert breaker.state == CircuitBreakerState.HALF_OPEN


@pytest.mark.asyncio
async def test_half_open_closes_on_success(config):
    """Test that HALF_OPEN closes after successful calls."""
    config.timeout_seconds = 0.1
    config.success_threshold = 2
    breaker = CircuitBreaker("test-plugin", config)
    
    # Open the circuit
    for _ in range(config.failure_threshold):
        await breaker.record_failure()
    
    # Wait for timeout -> HALF_OPEN
    await asyncio.sleep(0.2)
    await breaker.is_call_allowed()
    
    assert breaker.state == CircuitBreakerState.HALF_OPEN
    
    # Record successful calls
    await breaker.record_success()
    await breaker.record_success()
    
    # Should close
    assert breaker.state == CircuitBreakerState.CLOSED


@pytest.mark.asyncio
async def test_half_open_reopens_on_failure(config):
    """Test that HALF_OPEN reopens on failure."""
    config.timeout_seconds = 0.1
    breaker = CircuitBreaker("test-plugin", config)
    
    # Open the circuit
    for _ in range(config.failure_threshold):
        await breaker.record_failure()
    
    # Wait for timeout -> HALF_OPEN
    await asyncio.sleep(0.2)
    await breaker.is_call_allowed()
    
    # Record failure in HALF_OPEN
    await breaker.record_failure()
    
    # Should reopen
    assert breaker.state == CircuitBreakerState.OPEN


@pytest.mark.asyncio
async def test_circuit_breaker_statistics(config):
    """Test statistics collection."""
    breaker = CircuitBreaker("test-plugin", config)
    
    await breaker.record_success()
    await breaker.record_success()
    await breaker.record_failure()
    
    stats = breaker.get_statistics()
    
    assert stats.total_calls == 3
    assert stats.total_successes == 2
    assert stats.total_failures == 1
    assert stats.state == CircuitBreakerState.CLOSED


@pytest.mark.asyncio
async def test_circuit_breaker_registry():
    """Test circuit breaker registry."""
    registry = CircuitBreakerRegistry()
    
    # Configure a plugin
    config = CircuitBreakerConfig(failure_threshold=2)
    registry.configure("plugin-1", config)
    
    # Get breaker (should be created)
    breaker = await registry.get_breaker("plugin-1")
    assert breaker is not None
    
    # Record failure
    await registry.record_failure("plugin-1")
    await registry.record_failure("plugin-1")
    
    # Should be open
    state = await registry.get_state("plugin-1")
    assert state == CircuitBreakerState.OPEN


@pytest.mark.asyncio
async def test_reset_circuit_breaker(config):
    """Test resetting a circuit breaker."""
    breaker = CircuitBreaker("test-plugin", config)
    
    # Open the circuit
    for _ in range(config.failure_threshold):
        await breaker.record_failure()
    
    assert breaker.state == CircuitBreakerState.OPEN
    
    # Reset
    await breaker.reset()
    
    assert breaker.state == CircuitBreakerState.CLOSED
    assert await breaker.is_call_allowed() is True
