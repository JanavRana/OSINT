"""
Username OSINT Dispatcher.

The missing bridge between the investigation execution pipeline and the
38 YAML platform definitions.

This dispatcher:
1. Loads enabled platform plugins from the identity plugin registry
2. Configures rate limiters and circuit breakers per platform
3. Executes all platforms concurrently via asyncio.gather
4. Respects global concurrency limits (semaphore)
5. Handles per-platform failures without failing the whole batch
6. Returns RawResponseEnvelope objects compatible with the investigation pipeline
7. Reports partial success when some platforms fail
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple

import httpx

from app.connectors.types import (
    ConnectorStatus,
    Identifier,
    IdentifierType,
    RawResponseEnvelope,
)
from app.identity.plugin_base import DetectionOutcome, ExecutionContext, RawResult
from app.identity.plugin_runtime.circuit_breaker import get_circuit_breaker_registry
from app.identity.plugin_runtime.httpx_client import build_httpx_client
from app.identity.plugin_runtime.rate_limiter import get_rate_limiter
from app.identity.plugin_runtime.registry import PluginRegistry, get_registry
from app.identity.types import CircuitBreakerState, IdentifierType as IdentityIdentifierType
from app.identity.username.init import initialize_username_platforms
from app.identity.username.loader import PlatformLoader

logger = logging.getLogger(__name__)

# Global concurrency limit for username platform checks per investigation
GLOBAL_CONCURRENCY_LIMIT = 10


def _ensure_platforms_loaded(registry: PluginRegistry) -> None:
    """
    Ensure username platforms are registered. Initializes on first call.
    """
    from app.identity.types import IdentifierType as IdentityIdentifierType
    plugins = registry.filter_plugins(
        identifier_type=IdentityIdentifierType.USERNAME,
        enabled_only=True,
    )
    if not plugins:
        logger.info("Username platforms not yet loaded — initializing now")
        initialize_username_platforms()


def _build_definitions_map(plugin_ids: List[str], registry: PluginRegistry) -> dict:
    """Build a map of plugin_id -> PlatformDefinition for loaded platforms."""
    loader = PlatformLoader()
    definitions = loader.load_all_platforms()
    return {d.id: d for d in definitions if d.id in plugin_ids and d.enabled}


def _configure_rate_limiters(definitions_map: dict) -> None:
    """Configure the global rate limiter for each platform from its YAML definition."""
    rate_limiter = get_rate_limiter()
    for platform_id, definition in definitions_map.items():
        rpm = definition.rate_limit.requests_per_minute
        burst = definition.rate_limit.burst_size or rpm
        # Only configure if not already done (limiter retains state across calls)
        if platform_id not in rate_limiter._locks:
            rate_limiter.configure(
                plugin_id=platform_id,
                requests_per_minute=rpm,
                burst_size=burst,
            )


async def _execute_single_platform(
    plugin,
    definition,
    username: str,
    investigation_id: uuid.UUID,
    http_client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
) -> RawResponseEnvelope:
    """
    Execute a single platform check with concurrency, rate limit, and circuit breaker.

    Returns a RawResponseEnvelope regardless of success/failure.
    Never raises — failures are captured in the envelope.
    """
    platform_id = definition.id
    rate_limiter = get_rate_limiter()
    cb_registry = get_circuit_breaker_registry()

    started_at = datetime.now(timezone.utc)

    # Build the identifier for this check
    identifier = Identifier(value=username, type=IdentifierType.USERNAME)

    try:
        # Check circuit breaker before acquiring slots
        cb_allowed = await cb_registry.is_call_allowed(platform_id)
        if not cb_allowed:
            logger.debug(f"Circuit breaker OPEN for {platform_id}, skipping")
            return RawResponseEnvelope(
                connector_name=platform_id,
                identifier=identifier,
                status=ConnectorStatus.FAILED,
                error_message="Circuit breaker open — platform temporarily disabled",
                started_at=started_at,
                finished_at=datetime.now(timezone.utc),
            )

        # Acquire global concurrency slot
        async with semaphore:
            # Acquire rate limit token (may briefly wait)
            await rate_limiter.acquire(platform_id)

            # Build execution context
            context = ExecutionContext(
                identifier_type=IdentityIdentifierType.USERNAME,
                identifier_value=username,
                investigation_id=investigation_id,
                scan_id=uuid.uuid4(),
                task_id=uuid.uuid4(),
                http_client=http_client,
                rate_limiter=rate_limiter,
                logger=logger,
            )

            # Execute the platform plugin
            raw_result: RawResult = await plugin.execute(context)

    except asyncio.TimeoutError:
        finished_at = datetime.now(timezone.utc)
        logger.warning(f"Timeout executing platform {platform_id} for username={username}")
        await cb_registry.record_failure(platform_id)
        return RawResponseEnvelope(
            connector_name=platform_id,
            identifier=identifier,
            status=ConnectorStatus.TIMED_OUT,
            error_message="Platform check timed out",
            started_at=started_at,
            finished_at=finished_at,
        )

    except Exception as exc:
        finished_at = datetime.now(timezone.utc)
        logger.error(
            f"Platform {platform_id} failed for username={username}: {exc}",
            exc_info=True,
        )
        await cb_registry.record_failure(platform_id)
        return RawResponseEnvelope(
            connector_name=platform_id,
            identifier=identifier,
            status=ConnectorStatus.FAILED,
            error_message=str(exc),
            started_at=started_at,
            finished_at=datetime.now(timezone.utc),
        )

    finished_at = datetime.now(timezone.utc)

    # Record circuit breaker outcome
    if raw_result.success:
        await cb_registry.record_success(platform_id)
    else:
        await cb_registry.record_failure(platform_id)

    # Convert RawResult -> RawResponseEnvelope
    if raw_result.success and isinstance(raw_result.payload, DetectionOutcome):
        outcome = raw_result.payload
        # Store the outcome as a structured payload for the normalizer adapter
        payload_dict = {
            "platform_id": platform_id,
            "username": username,
            "exists": outcome.exists,
            "http_status": outcome.http_status,
            "evidence_fields": outcome.evidence_fields or {},
            "raw_snapshot_ref": outcome.raw_snapshot_ref,
            "strategy_confidence_hint": outcome.strategy_confidence_hint,
            "profile_url": definition.get_profile_url(username),
            "platform_display_name": definition.display_name,
            "platform_category": definition.category.value if hasattr(definition.category, 'value') else str(definition.category),
            "platform_homepage": str(definition.homepage),
            "base_reliability": definition.confidence_rules.base_reliability,
            "duration_ms": raw_result.duration_ms,
        }

        return RawResponseEnvelope(
            connector_name=f"username_platform:{platform_id}",
            identifier=identifier,
            status=ConnectorStatus.SUCCEEDED,
            raw_payload=payload_dict,
            started_at=started_at,
            finished_at=finished_at,
            metadata={
                "platform_id": platform_id,
                "exists": str(outcome.exists),
                "http_status": outcome.http_status,
            },
        )
    else:
        return RawResponseEnvelope(
            connector_name=f"username_platform:{platform_id}",
            identifier=identifier,
            status=ConnectorStatus.FAILED,
            error_message=raw_result.error or "Platform check returned no result",
            started_at=started_at,
            finished_at=finished_at,
        )


async def dispatch_username_osint(
    username: str,
    investigation_id: uuid.UUID,
    platforms_dir=None,
) -> List[RawResponseEnvelope]:
    """
    Dispatch username OSINT across all enabled platform definitions.

    This is the primary entry point called by InvestigationService when
    identifier.type == USERNAME.

    Args:
        username: The username to investigate
        investigation_id: Investigation ID for context/logging
        platforms_dir: Optional custom platforms directory (for testing)

    Returns:
        List of RawResponseEnvelope, one per platform attempted.
        Successes have status=SUCCEEDED with raw_payload containing DetectionOutcome data.
        Failures have status=FAILED/TIMED_OUT with error_message.
        Never raises — the pipeline gets partial results on failure.
    """
    logger.info(
        f"Dispatching username OSINT: username={username!r}, "
        f"investigation_id={investigation_id}"
    )

    # Ensure platforms are loaded into the identity registry
    registry = get_registry()
    _ensure_platforms_loaded(registry)

    # Get enabled platform plugin IDs
    enabled_ids = registry.filter_plugins(
        identifier_type=IdentityIdentifierType.USERNAME,
        enabled_only=True,
    )

    if not enabled_ids:
        logger.warning("No enabled username platforms found. Investigation will have 0 results.")
        return []

    logger.info(f"Found {len(enabled_ids)} enabled platforms to check")

    # Load platform definitions (for rate limit config, URLs, etc.)
    loader = PlatformLoader(platforms_dir)
    all_definitions = loader.load_all_platforms()
    definitions_map = {d.id: d for d in all_definitions if d.id in enabled_ids and d.enabled}

    # Configure rate limiters from YAML definitions
    _configure_rate_limiters(definitions_map)

    # Collect (plugin, definition) pairs to execute
    tasks_to_run: List[Tuple] = []
    for platform_id in enabled_ids:
        plugin = registry.get(platform_id)
        definition = definitions_map.get(platform_id)

        if plugin is None or definition is None:
            logger.warning(f"Plugin or definition missing for {platform_id}, skipping")
            continue

        tasks_to_run.append((plugin, definition))

    if not tasks_to_run:
        logger.warning("No executable platform tasks after filtering")
        return []

    logger.info(f"Executing {len(tasks_to_run)} platform checks concurrently")

    # Build shared HTTP client for this dispatch
    http_client = build_httpx_client()

    # Global concurrency semaphore
    semaphore = asyncio.Semaphore(GLOBAL_CONCURRENCY_LIMIT)

    try:
        # Execute all platforms concurrently
        results = await asyncio.gather(
            *[
                _execute_single_platform(
                    plugin=plugin,
                    definition=definition,
                    username=username,
                    investigation_id=investigation_id,
                    http_client=http_client,
                    semaphore=semaphore,
                )
                for plugin, definition in tasks_to_run
            ],
            return_exceptions=False,  # Each task handles its own exceptions
        )
    finally:
        # Always close the HTTP client
        await http_client.aclose()

    envelopes = list(results)

    succeeded = sum(1 for e in envelopes if e.status == ConnectorStatus.SUCCEEDED)
    failed = len(envelopes) - succeeded

    logger.info(
        f"Username OSINT complete: {succeeded} succeeded, {failed} failed "
        f"out of {len(envelopes)} platforms for username={username!r}"
    )

    return envelopes
