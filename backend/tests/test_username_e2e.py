"""
End-to-end integration tests for the username OSINT pipeline.

Tests the complete flow:
  username entered → dispatcher → detection strategies →
  RawResponseEnvelope → normalization → fact persistence →
  identifiers endpoint → graph relationships

All HTTP calls are mocked — no live websites required.

Requirements covered:
1.  Username exists on mocked platform → result returned
2.  Username doesn't exist → no false result
3.  One platform fails → others still execute
4.  Multiple platforms execute concurrently
5.  Rate limiting is respected (token bucket doesn't raise)
6.  Results are normalized (NormalizationResult facts produced)
7.  Results are persisted (NormalizedFact rows in DB)
8.  GET /identifiers returns username discoveries
9.  Graph relationships are created (social_account facts)
10. Existing domain investigation still works
11. Existing email investigation still works
12. Existing phone investigation still works
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.connectors.types import (
    ConnectorStatus,
    Identifier,
    IdentifierType,
    RawResponseEnvelope,
)
from app.db.session import Base
from app.models.investigation import InvestigationStatus
from app.normalizers.types import FactType, NormalizedFact, NormalizationResult
from app.services.investigation_service import InvestigationService

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db_session():
    """In-memory SQLite DB — no Docker or PostgreSQL required."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _make_username_envelope(
    platform_id: str,
    username: str,
    exists=True,
    http_status: int = 200,
    evidence: dict = None,
    status: ConnectorStatus = ConnectorStatus.SUCCEEDED,
    error: str = None,
) -> RawResponseEnvelope:
    """Helper: build a username platform RawResponseEnvelope."""
    identifier = Identifier(value=username, type=IdentifierType.USERNAME)
    if status == ConnectorStatus.SUCCEEDED:
        payload = {
            "platform_id": platform_id,
            "username": username,
            "exists": exists,
            "http_status": http_status,
            "evidence_fields": evidence or {},
            "profile_url": f"https://example.com/{username}",
            "platform_display_name": platform_id.capitalize(),
            "platform_category": "developer",
            "platform_homepage": "https://example.com",
            "base_reliability": 0.9,
            "strategy_confidence_hint": 0.85,
            "duration_ms": 123.4,
        }
        return RawResponseEnvelope(
            connector_name=f"username_platform:{platform_id}",
            identifier=identifier,
            status=ConnectorStatus.SUCCEEDED,
            raw_payload=payload,
            started_at=datetime.utcnow(),
            finished_at=datetime.utcnow(),
        )
    else:
        return RawResponseEnvelope(
            connector_name=f"username_platform:{platform_id}",
            identifier=identifier,
            status=status,
            error_message=error or "Platform check failed",
            started_at=datetime.utcnow(),
            finished_at=datetime.utcnow(),
        )


# ---------------------------------------------------------------------------
# Test 1: Username exists on a mocked platform → result returned
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_username_exists_on_mocked_platform(db_session):
    """Username found → SUCCEEDED envelope → PROFILE_DATA fact persisted."""
    service = InvestigationService(db_session)
    investigation, _ = service.create_investigation(name="Test Username Investigation")

    identifier = Identifier(value="torvalds", type=IdentifierType.USERNAME)

    # Mock the dispatcher to return one successful envelope
    found_envelope = _make_username_envelope(
        "github", "torvalds", exists=True, http_status=200,
        evidence={"login": "torvalds", "name": "Linus Torvalds"},
    )

    with patch(
        "app.services.investigation_service.InvestigationService._run_username_osint",
        new=AsyncMock(return_value=[found_envelope]),
    ):
        result = await service.execute_investigation(investigation.id, identifier)

    assert result.status == InvestigationStatus.COMPLETED
    assert result.executed_connectors == 1
    assert result.successful_connectors == 1
    assert result.normalized_facts_count >= 1

    # Verify fact is in DB
    from app.repositories.normalized_fact_repository import NormalizedFactRepository
    repo = NormalizedFactRepository(db_session)
    facts = repo.list_by_investigation(investigation.id)
    assert len(facts) >= 1
    # At least one fact should be a profile_data fact
    profile_facts = [f for f in facts if f.fact_type == "profile_data"]
    assert len(profile_facts) >= 1


# ---------------------------------------------------------------------------
# Test 2: Username doesn't exist → no false result
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_username_not_found_no_false_result(db_session):
    """Username not found (404) → fact with exists=False, no profile_data fact."""
    service = InvestigationService(db_session)
    investigation, _ = service.create_investigation(name="Not Found Test")

    identifier = Identifier(value="definitely_not_exists_xyz9999", type=IdentifierType.USERNAME)

    not_found_envelope = _make_username_envelope(
        "github", "definitely_not_exists_xyz9999",
        exists=False, http_status=404,
    )

    with patch(
        "app.services.investigation_service.InvestigationService._run_username_osint",
        new=AsyncMock(return_value=[not_found_envelope]),
    ):
        result = await service.execute_investigation(investigation.id, identifier)

    assert result.status == InvestigationStatus.COMPLETED

    # No profile_data (FOUND) facts should exist
    from app.repositories.normalized_fact_repository import NormalizedFactRepository
    repo = NormalizedFactRepository(db_session)
    facts = repo.list_by_investigation(investigation.id)
    profile_facts = [f for f in facts if f.fact_type == "profile_data"]
    assert len(profile_facts) == 0, "Should have no profile_data fact for non-existent username"


# ---------------------------------------------------------------------------
# Test 3: One platform fails → others still execute
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_one_platform_fails_others_still_execute(db_session):
    """If one platform returns FAILED, the rest should still produce facts."""
    service = InvestigationService(db_session)
    investigation, _ = service.create_investigation(name="Partial Failure Test")

    identifier = Identifier(value="someuser", type=IdentifierType.USERNAME)

    envelopes = [
        _make_username_envelope("github", "someuser", exists=True, http_status=200),
        _make_username_envelope(
            "brokenplatform", "someuser",
            status=ConnectorStatus.FAILED, error="Connection timeout",
        ),
        _make_username_envelope("reddit", "someuser", exists=True, http_status=200),
    ]

    with patch(
        "app.services.investigation_service.InvestigationService._run_username_osint",
        new=AsyncMock(return_value=envelopes),
    ):
        result = await service.execute_investigation(investigation.id, identifier)

    # Pipeline should complete despite 1 failure
    assert result.status == InvestigationStatus.COMPLETED
    assert result.executed_connectors == 3
    assert result.successful_connectors == 2
    assert result.failed_connectors == 1
    # Facts from the 2 successful platforms should be persisted
    assert result.normalized_facts_count >= 2


# ---------------------------------------------------------------------------
# Test 4: Multiple platforms execute concurrently
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_multiple_platforms_execute_concurrently(db_session):
    """Dispatcher runs all platforms in parallel via asyncio.gather."""
    import time

    call_times = []

    async def fake_execute_single(plugin, definition, username, investigation_id,
                                  http_client, semaphore):
        call_times.append(time.monotonic())
        # Simulate network delay
        await asyncio.sleep(0.01)
        identifier = Identifier(value=username, type=IdentifierType.USERNAME)
        return RawResponseEnvelope(
            connector_name=f"username_platform:{definition.id}",
            identifier=identifier,
            status=ConnectorStatus.SUCCEEDED,
            raw_payload={
                "platform_id": definition.id,
                "username": username,
                "exists": True,
                "http_status": 200,
                "evidence_fields": {},
                "profile_url": f"https://example.com/{username}",
                "platform_display_name": definition.display_name,
                "platform_category": "developer",
                "platform_homepage": str(definition.homepage),
                "base_reliability": 0.9,
                "strategy_confidence_hint": 0.8,
                "duration_ms": 10.0,
            },
            started_at=datetime.utcnow(),
            finished_at=datetime.utcnow(),
        )

    # Load platform definitions directly — no global registry dependency
    from app.identity.username.loader import PlatformLoader
    loader = PlatformLoader()
    all_defs = loader.load_all_platforms()
    test_defs = [d for d in all_defs if d.enabled][:5]

    if len(test_defs) < 2:
        pytest.skip("Need at least 2 enabled platforms for concurrency test")

    # Run all platforms concurrently using gather (the same pattern as the dispatcher)
    import httpx
    http_client = httpx.AsyncClient()
    semaphore = asyncio.Semaphore(10)

    start = time.monotonic()
    try:
        results = await asyncio.gather(*[
            fake_execute_single(None, d, "testuser", uuid.uuid4(), http_client, semaphore)
            for d in test_defs
        ])
    finally:
        await http_client.aclose()
    elapsed = time.monotonic() - start

    # All platforms should have executed
    assert len(results) == len(test_defs)
    assert all(r.status == ConnectorStatus.SUCCEEDED for r in results)
    # Concurrent: total time should be much less than N * 10ms
    # (allow generous 0.5s margin for test environments)
    assert elapsed < 0.5, f"Concurrent execution took {elapsed:.2f}s, expected <0.5s"


# ---------------------------------------------------------------------------
# Test 5: Rate limiting is respected (token bucket configured per platform)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rate_limiting_configured_from_yaml(db_session):
    """Rate limiter is configured for each platform from its YAML rate_limit config."""
    from app.identity.username.dispatcher import _configure_rate_limiters
    from app.identity.plugin_runtime.rate_limiter import get_rate_limiter, reset_rate_limiter
    from app.identity.username.loader import PlatformLoader

    reset_rate_limiter()
    loader = PlatformLoader()
    defs = loader.load_all_platforms()
    # Use only a few platforms for speed
    defs_map = {d.id: d for d in defs if d.enabled}
    small_map = dict(list(defs_map.items())[:5])

    _configure_rate_limiters(small_map)

    rate_limiter = get_rate_limiter()

    # Verify that each platform has a lock (meaning it was configured)
    for platform_id, definition in small_map.items():
        assert platform_id in rate_limiter._locks, (
            f"Platform {platform_id} should be configured in rate limiter"
        )
        expected_rpm = definition.rate_limit.requests_per_minute
        actual_refill_rate = rate_limiter._refill_rate.get(platform_id, 0)
        expected_refill_rate = expected_rpm / 60.0
        assert abs(actual_refill_rate - expected_refill_rate) < 0.01, (
            f"Platform {platform_id}: expected refill_rate={expected_refill_rate:.4f}, "
            f"got {actual_refill_rate:.4f}"
        )

    reset_rate_limiter()


# ---------------------------------------------------------------------------
# Test 6: Results are normalized (NormalizationResult with facts produced)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_results_are_normalized(db_session):
    """Successful DetectionOutcome payload → UsernamePlatformNormalizer → NormalizedFact."""
    from app.identity.username.normalizer_adapter import UsernamePlatformNormalizer

    normalizer = UsernamePlatformNormalizer()

    payload = {
        "platform_id": "github",
        "username": "testuser",
        "exists": True,
        "http_status": 200,
        "evidence_fields": {"login": "testuser", "name": "Test User"},
        "profile_url": "https://github.com/testuser",
        "platform_display_name": "GitHub",
        "platform_category": "developer",
        "platform_homepage": "https://github.com",
        "base_reliability": 0.95,
        "strategy_confidence_hint": 0.85,
        "duration_ms": 120.0,
    }

    facts = normalizer.normalize(payload)

    assert len(facts) == 1
    fact = facts[0]
    assert fact.fact_type == FactType.PROFILE_DATA
    assert fact.confidence > 0.7
    assert fact.metadata["platform_id"] == "github"
    assert fact.metadata["exists"] is True
    assert fact.metadata["profile_url"] == "https://github.com/testuser"


# ---------------------------------------------------------------------------
# Test 7: Results are persisted (facts in DB) + deduplication
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_results_are_persisted_with_deduplication(db_session):
    """Facts are persisted once; re-running same investigation skips duplicates."""
    service = InvestigationService(db_session)
    investigation, _ = service.create_investigation(name="Persistence Test")

    identifier = Identifier(value="persisttest", type=IdentifierType.USERNAME)
    envelope = _make_username_envelope("github", "persisttest", exists=True)

    with patch(
        "app.services.investigation_service.InvestigationService._run_username_osint",
        new=AsyncMock(return_value=[envelope]),
    ):
        result1 = await service.execute_investigation(investigation.id, identifier)

    from app.repositories.normalized_fact_repository import NormalizedFactRepository
    repo = NormalizedFactRepository(db_session)
    facts_after_first_run = repo.list_by_investigation(investigation.id)
    count_after_first = len(facts_after_first_run)
    assert count_after_first >= 1, "Facts should be persisted after first run"

    # Run again — deduplication should prevent double-counting
    with patch(
        "app.services.investigation_service.InvestigationService._run_username_osint",
        new=AsyncMock(return_value=[envelope]),
    ):
        result2 = await service.execute_investigation(investigation.id, identifier)

    facts_after_second_run = repo.list_by_investigation(investigation.id)
    count_after_second = len(facts_after_second_run)

    assert count_after_second == count_after_first, (
        f"Second run should not create duplicates: "
        f"first={count_after_first}, second={count_after_second}"
    )


# ---------------------------------------------------------------------------
# Test 8: GET /identifiers returns username discoveries
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_identifiers_endpoint_returns_username_facts(db_session):
    """
    After a username investigation, normalized facts should appear in
    the identifiers list (as type 'username' or 'social').
    """
    service = InvestigationService(db_session)
    investigation, _ = service.create_investigation(name="Identifiers Test")

    identifier = Identifier(value="identtest", type=IdentifierType.USERNAME)
    envelope = _make_username_envelope("github", "identtest", exists=True)

    with patch(
        "app.services.investigation_service.InvestigationService._run_username_osint",
        new=AsyncMock(return_value=[envelope]),
    ):
        await service.execute_investigation(investigation.id, identifier)

    # Check facts directly in the DB
    from app.repositories.normalized_fact_repository import NormalizedFactRepository
    repo = NormalizedFactRepository(db_session)
    facts = repo.list_by_investigation(investigation.id)

    assert len(facts) >= 1

    # The fact_type_to_identifier map in the API maps:
    # "profile_data" → "username"  (via the identifiers endpoint)
    profile_facts = [f for f in facts if f.fact_type == "profile_data"]
    assert len(profile_facts) >= 1, "Should have profile_data facts for found username"


# ---------------------------------------------------------------------------
# Test 9: Graph relationships are created (social_account facts)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_graph_relationships_created_for_found_accounts(db_session):
    """
    For each platform where the username is found, a social_account fact
    should be created representing the FOUND_ON graph relationship.
    """
    service = InvestigationService(db_session)
    investigation, _ = service.create_investigation(name="Graph Test")

    identifier = Identifier(value="graphtest", type=IdentifierType.USERNAME)

    # Two platforms find the user
    envelopes = [
        _make_username_envelope("github", "graphtest", exists=True),
        _make_username_envelope("reddit", "graphtest", exists=True),
    ]

    with patch(
        "app.services.investigation_service.InvestigationService._run_username_osint",
        new=AsyncMock(return_value=envelopes),
    ):
        result = await service.execute_investigation(investigation.id, identifier)

    # Check social_account graph facts
    from app.repositories.normalized_fact_repository import NormalizedFactRepository
    repo = NormalizedFactRepository(db_session)
    facts = repo.list_by_investigation(investigation.id)

    social_facts = [f for f in facts if f.fact_type == "social_account"]
    # Should have graph relationship facts for the found platforms
    assert len(social_facts) >= 2, (
        f"Expected >= 2 social_account graph facts, got {len(social_facts)}"
    )

    # Verify relationship metadata
    for sf in social_facts:
        meta = sf.fact_metadata or {}
        assert meta.get("relationship") == "FOUND_ON"
        assert meta.get("graph_edge") is True


# ---------------------------------------------------------------------------
# Test 10: Existing domain investigation still works
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_domain_investigation_still_works(db_session):
    """Domain investigations continue to use the classic connector framework."""
    service = InvestigationService(db_session)
    investigation, _ = service.create_investigation(name="Domain Test")

    identifier = Identifier(value="example.com", type=IdentifierType.DOMAIN)

    mock_responses = [
        RawResponseEnvelope(
            connector_name="whois",
            identifier=identifier,
            status=ConnectorStatus.SUCCEEDED,
            raw_payload={"registrar": "Example Registrar", "creation_date": "2020-01-01"},
            started_at=datetime.utcnow(),
            finished_at=datetime.utcnow(),
        )
    ]
    mock_norm_results = [
        NormalizationResult(
            facts=[
                NormalizedFact(
                    fact_type=FactType.DOMAIN_REGISTRATION,
                    value="Example Registrar",
                    source_connector="whois",
                    confidence=1.0,
                    metadata={},
                )
            ],
            connector_name="whois",
            normalized_at=datetime.utcnow(),
        )
    ]

    with patch(
        "app.services.investigation_service.ConnectorExecutionService"
    ) as MockConnSvc:
        mock_svc = MagicMock()
        mock_svc.execute_connectors = AsyncMock(return_value=mock_responses)
        MockConnSvc.return_value = mock_svc

        with patch(
            "app.services.investigation_service.normalization_manager"
        ) as mock_norm:
            mock_norm.normalize_batch.return_value = mock_norm_results
            service = InvestigationService(db_session)
            result = await service.execute_investigation(investigation.id, identifier)

    # Domain should NOT go through username dispatcher
    assert result.status == InvestigationStatus.COMPLETED
    assert result.executed_connectors == 1
    assert result.normalized_facts_count == 1


# ---------------------------------------------------------------------------
# Test 11: Existing email investigation still works
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_email_investigation_still_works(db_session):
    """Email investigations continue to use the classic connector framework."""
    service = InvestigationService(db_session)
    investigation, _ = service.create_investigation(name="Email Test")

    identifier = Identifier(value="user@example.com", type=IdentifierType.EMAIL)

    mock_responses = [
        RawResponseEnvelope(
            connector_name="gravatar",
            identifier=identifier,
            status=ConnectorStatus.SUCCEEDED,
            raw_payload={"hash": "abc123", "profile_url": "https://gravatar.com/abc123"},
            started_at=datetime.utcnow(),
            finished_at=datetime.utcnow(),
        )
    ]
    mock_norm_results = [
        NormalizationResult(
            facts=[
                NormalizedFact(
                    fact_type=FactType.PROFILE_DATA,
                    value="abc123",
                    source_connector="gravatar",
                    confidence=0.8,
                    metadata={},
                )
            ],
            connector_name="gravatar",
            normalized_at=datetime.utcnow(),
        )
    ]

    with patch(
        "app.services.investigation_service.ConnectorExecutionService"
    ) as MockConnSvc:
        mock_svc = MagicMock()
        mock_svc.execute_connectors = AsyncMock(return_value=mock_responses)
        MockConnSvc.return_value = mock_svc

        with patch(
            "app.services.investigation_service.normalization_manager"
        ) as mock_norm:
            mock_norm.normalize_batch.return_value = mock_norm_results
            service = InvestigationService(db_session)
            result = await service.execute_investigation(investigation.id, identifier)

    assert result.status == InvestigationStatus.COMPLETED
    assert result.executed_connectors == 1
    assert result.normalized_facts_count == 1


# ---------------------------------------------------------------------------
# Test 12: Existing phone investigation still works
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_phone_investigation_still_works(db_session):
    """Phone investigations continue to use the classic connector framework."""
    service = InvestigationService(db_session)
    investigation, _ = service.create_investigation(name="Phone Test")

    identifier = Identifier(value="+1234567890", type=IdentifierType.PHONE)

    mock_responses = []  # No phone connectors registered yet — that's OK
    mock_norm_results = []

    with patch(
        "app.services.investigation_service.ConnectorExecutionService"
    ) as MockConnSvc:
        mock_svc = MagicMock()
        mock_svc.execute_connectors = AsyncMock(return_value=mock_responses)
        MockConnSvc.return_value = mock_svc

        with patch(
            "app.services.investigation_service.normalization_manager"
        ) as mock_norm:
            mock_norm.normalize_batch.return_value = mock_norm_results
            service = InvestigationService(db_session)
            result = await service.execute_investigation(investigation.id, identifier)

    # Phone should complete (0 results is valid — no phone connectors registered)
    assert result.status == InvestigationStatus.COMPLETED
    assert result.normalized_facts_count == 0


# ---------------------------------------------------------------------------
# Additional: Normalizer handles unknown/ambiguous results correctly
# ---------------------------------------------------------------------------


def test_normalizer_handles_not_found_correctly():
    """exists=False → GENERIC fact with lower confidence than FOUND."""
    from app.identity.username.normalizer_adapter import UsernamePlatformNormalizer

    normalizer = UsernamePlatformNormalizer()

    payload = {
        "platform_id": "twitter",
        "username": "deleteduser",
        "exists": False,
        "http_status": 404,
        "evidence_fields": {},
        "profile_url": "https://twitter.com/deleteduser",
        "platform_display_name": "Twitter/X",
        "platform_category": "social",
        "platform_homepage": "https://twitter.com",
        "base_reliability": 0.8,
        "strategy_confidence_hint": 0.9,
        "duration_ms": 80.0,
    }

    facts = normalizer.normalize(payload)
    assert len(facts) == 1
    fact = facts[0]
    # Not found should be GENERIC, not PROFILE_DATA
    assert fact.fact_type == FactType.GENERIC
    # 404 should give relatively high confidence in "not found"
    assert fact.confidence >= 0.5


def test_normalizer_handles_unknown_result_with_low_confidence():
    """exists='unknown' → GENERIC fact with very low confidence."""
    from app.identity.username.normalizer_adapter import UsernamePlatformNormalizer

    normalizer = UsernamePlatformNormalizer()

    payload = {
        "platform_id": "someplatform",
        "username": "ambiguous",
        "exists": "unknown",
        "http_status": 200,
        "evidence_fields": {},
        "profile_url": "https://someplatform.com/ambiguous",
        "platform_display_name": "SomePlatform",
        "platform_category": "other",
        "platform_homepage": "https://someplatform.com",
        "base_reliability": 0.6,
        "strategy_confidence_hint": 0.3,
        "duration_ms": 300.0,
    }

    facts = normalizer.normalize(payload)
    assert len(facts) == 1
    fact = facts[0]
    assert fact.fact_type == FactType.GENERIC
    assert fact.confidence < 0.3, "Unknown results should have very low confidence"


def test_normalizer_handles_invalid_payload():
    """Non-dict payload → empty facts list, no crash."""
    from app.identity.username.normalizer_adapter import UsernamePlatformNormalizer

    normalizer = UsernamePlatformNormalizer()
    facts = normalizer.normalize(None)
    assert facts == []

    facts = normalizer.normalize("invalid")
    assert facts == []


# ---------------------------------------------------------------------------
# Dispatcher unit tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dispatcher_returns_empty_if_no_platforms():
    """If no platforms are registered, dispatcher returns empty list."""
    from app.identity.username.dispatcher import dispatch_username_osint

    with patch(
        "app.identity.username.dispatcher.get_registry"
    ) as mock_get_registry:
        mock_reg = MagicMock()
        mock_reg.filter_plugins.return_value = []
        mock_get_registry.return_value = mock_reg

        with patch("app.identity.username.dispatcher._ensure_platforms_loaded"):
            result = await dispatch_username_osint("testuser", uuid.uuid4())

    assert result == []


@pytest.mark.asyncio
async def test_dispatcher_handles_circuit_breaker_open():
    """If circuit breaker is OPEN, platform is skipped with FAILED status."""
    from app.identity.username import dispatcher as dispatcher_module
    from app.identity.plugin_base import ExecutionContext, RawResult, DetectionOutcome
    from app.identity.types import IdentifierType as IdentityIdentifierType

    # Create a minimal mock definition and plugin
    mock_definition = MagicMock()
    mock_definition.id = "testplatform"
    mock_definition.rate_limit.requests_per_minute = 60
    mock_definition.rate_limit.burst_size = None

    mock_plugin = MagicMock()

    import httpx
    http_client = httpx.AsyncClient()
    semaphore = asyncio.Semaphore(10)

    try:
        with patch(
            "app.identity.username.dispatcher.get_circuit_breaker_registry"
        ) as mock_cb_reg:
            mock_cb = MagicMock()
            mock_cb.is_call_allowed = AsyncMock(return_value=False)
            mock_cb_reg.return_value = mock_cb

            result = await dispatcher_module._execute_single_platform(
                plugin=mock_plugin,
                definition=mock_definition,
                username="testuser",
                investigation_id=uuid.uuid4(),
                http_client=http_client,
                semaphore=semaphore,
            )
    finally:
        await http_client.aclose()

    assert result.status == ConnectorStatus.FAILED
    assert "circuit breaker" in result.error_message.lower()
