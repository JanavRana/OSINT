"""
Real httpx HTTP client for plugin execution.

Replaces the stub HTTPClientPool with a working httpx.AsyncClient that
handles timeouts, redirects, connection pooling, and proper cleanup.
"""

import logging
from contextlib import asynccontextmanager
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# Default timeout for platform checks (seconds)
DEFAULT_TIMEOUT = httpx.Timeout(
    connect=5.0,
    read=10.0,
    write=5.0,
    pool=5.0,
)

# Default headers that look like a real browser
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def build_httpx_client(
    timeout: Optional[httpx.Timeout] = None,
    max_redirects: int = 5,
    verify_ssl: bool = True,
) -> httpx.AsyncClient:
    """
    Build a configured httpx.AsyncClient.

    Args:
        timeout: Custom timeout (defaults to DEFAULT_TIMEOUT)
        max_redirects: Maximum number of redirects to follow
        verify_ssl: Whether to verify SSL certificates

    Returns:
        Configured httpx.AsyncClient ready for use
    """
    limits = httpx.Limits(
        max_connections=100,
        max_keepalive_connections=20,
        keepalive_expiry=5.0,
    )

    client = httpx.AsyncClient(
        timeout=timeout or DEFAULT_TIMEOUT,
        limits=limits,
        follow_redirects=True,
        max_redirects=max_redirects,
        verify=verify_ssl,
        headers=DEFAULT_HEADERS,
    )

    logger.debug(
        f"Built httpx client: timeout={timeout or DEFAULT_TIMEOUT}, "
        f"max_redirects={max_redirects}"
    )

    return client


@asynccontextmanager
async def managed_http_client(
    timeout: Optional[httpx.Timeout] = None,
    max_redirects: int = 5,
):
    """
    Context manager that creates and properly closes an httpx client.

    Usage:
        async with managed_http_client() as client:
            response = await client.get(url)
    """
    client = build_httpx_client(timeout=timeout, max_redirects=max_redirects)
    try:
        yield client
    finally:
        await client.aclose()


# Module-level shared client for reuse across platform checks in a single scan
_shared_client: Optional[httpx.AsyncClient] = None


async def get_shared_client() -> httpx.AsyncClient:
    """
    Get (or create) the shared httpx client for the current process.

    This client is reused across multiple platform checks to benefit from
    connection pooling. Call close_shared_client() at shutdown.
    """
    global _shared_client
    if _shared_client is None or _shared_client.is_closed:
        _shared_client = build_httpx_client()
        logger.debug("Created shared httpx client")
    return _shared_client


async def close_shared_client() -> None:
    """Close the shared httpx client and release connections."""
    global _shared_client
    if _shared_client and not _shared_client.is_closed:
        await _shared_client.aclose()
        _shared_client = None
        logger.debug("Closed shared httpx client")
