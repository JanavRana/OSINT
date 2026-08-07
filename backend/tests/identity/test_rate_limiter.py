"""
Tests for rate limiter.
"""

import asyncio
import pytest
import time

from app.identity.plugin_runtime.rate_limiter import RateLimiter


@pytest.fixture
def rate_limiter():
    """Provide a fresh rate limiter for each test."""
    return RateLimiter()


def test_configure_rate_limiter(rate_limiter):
    """Test configuring a rate limiter for a plugin."""
    rate_limiter.configure("test-plugin", requests_per_minute=60)
    
    stats = rate_limiter.get_statistics("test-plugin")
    assert stats["configured"] is True
    assert stats["max_tokens"] == 60


@pytest.mark.asyncio
async def test_acquire_tokens(rate_limiter):
    """Test acquiring tokens."""
    rate_limiter.configure("test-plugin", requests_per_minute=60)
    
    # Should acquire immediately
    start = time.monotonic()
    await rate_limiter.acquire("test-plugin")
    elapsed = time.monotonic() - start
    
    assert elapsed < 0.1  # Should be instant


@pytest.mark.asyncio
async def test_rate_limiting_blocks(rate_limiter):
    """Test that rate limiter blocks when tokens exhausted."""
    # Configure very low rate: 2 requests per minute
    rate_limiter.configure("test-plugin", requests_per_minute=2, burst_size=2)
    
    # Exhaust tokens
    await rate_limiter.acquire("test-plugin")
    await rate_limiter.acquire("test-plugin")
    
    # Next acquire should block
    start = time.monotonic()
    await rate_limiter.acquire("test-plugin")
    elapsed = time.monotonic() - start
    
    # Should have waited for token refill
    assert elapsed > 0.5  # At least some delay


def test_try_acquire_non_blocking(rate_limiter):
    """Test try_acquire without blocking."""
    rate_limiter.configure("test-plugin", requests_per_minute=2, burst_size=2)
    
    # First two should succeed
    assert rate_limiter.try_acquire("test-plugin") is True
    assert rate_limiter.try_acquire("test-plugin") is True
    
    # Third should fail (no blocking)
    assert rate_limiter.try_acquire("test-plugin") is False


def test_get_available_tokens(rate_limiter):
    """Test checking available tokens."""
    rate_limiter.configure("test-plugin", requests_per_minute=10, burst_size=10)
    
    assert rate_limiter.get_available_tokens("test-plugin") == 10
    
    rate_limiter.try_acquire("test-plugin", tokens=3)
    assert rate_limiter.get_available_tokens("test-plugin") == 7


def test_token_refill(rate_limiter):
    """Test that tokens refill over time."""
    rate_limiter.configure("test-plugin", requests_per_minute=60, burst_size=5)
    
    # Exhaust tokens
    for _ in range(5):
        rate_limiter.try_acquire("test-plugin")
    
    assert rate_limiter.get_available_tokens("test-plugin") < 1
    
    # Wait for refill (60 req/min = 1 req/second)
    time.sleep(1.1)
    
    # Should have refilled
    assert rate_limiter.get_available_tokens("test-plugin") >= 1


def test_unconfigured_plugin_allowed(rate_limiter):
    """Test that unconfigured plugins are allowed through."""
    available = rate_limiter.get_available_tokens("unconfigured-plugin")
    assert available == float('inf')


def test_get_request_rate(rate_limiter):
    """Test request rate calculation."""
    rate_limiter.configure("test-plugin", requests_per_minute=60)
    
    # Make some requests
    for _ in range(5):
        rate_limiter.try_acquire("test-plugin")
    
    rate = rate_limiter.get_request_rate("test-plugin", window_seconds=60)
    assert rate >= 0  # Should have some rate


def test_reset_rate_limiter(rate_limiter):
    """Test resetting a rate limiter."""
    rate_limiter.configure("test-plugin", requests_per_minute=5, burst_size=5)
    
    # Exhaust tokens
    for _ in range(5):
        rate_limiter.try_acquire("test-plugin")
    
    assert rate_limiter.get_available_tokens("test-plugin") < 1
    
    # Reset
    rate_limiter.reset("test-plugin")
    
    # Should be back to full
    assert rate_limiter.get_available_tokens("test-plugin") == 5
