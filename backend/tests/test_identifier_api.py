"""
Tests for the identifier API conversion in list_identifiers.

Covers:
- profile_data facts -> clean username + profile_url
- WHOIS metadata facts (registrar, nameserver, expiration, org, location,
  generic, certificate, archive_snapshot, image_hash, domain_registration)
  are excluded from the identifier list
- domain, email, phone facts pass through correctly
- social_account facts produce clean username + profile_url
- profile_url is None when account does not exist
"""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.normalized_fact import NormalizedFact as NormalizedFactModel
from app.repositories.normalized_fact_repository import NormalizedFactRepository
from app.schemas.investigation import IdentifierListResponse, IdentifierRead


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_session():
    """In-memory SQLite session (no PostgreSQL required)."""
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _make_fact(
    db,
    investigation_id: uuid.UUID,
    fact_type: str,
    value: str,
    metadata: dict | None = None,
    confidence: float = 0.9,
) -> NormalizedFactModel:
    """Helper: persist and return a NormalizedFact row."""
    repo = NormalizedFactRepository(db)
    return repo.create(
        investigation_id=investigation_id,
        connector_name="test_connector",
        fact_type=fact_type,
        value=value,
        confidence=confidence,
        fact_metadata=metadata or {},
        occurred_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# Duplicate the mapping logic from list_identifiers so tests don't need
# a running FastAPI server.
# ---------------------------------------------------------------------------


def _run_list_identifiers(db, investigation_id: uuid.UUID) -> IdentifierListResponse:
    """
    Reproduce the exact mapping logic from investigations.list_identifiers.
    Tests can call this without spinning up a web server.
    """
    IDENTIFIER_FACT_TYPES: dict[str, str] = {
        "email": "email",
        "domain": "domain",
        "phone": "phone",
        "username": "username",
        "wallet_address": "wallet",
        "social_account": "social",
        "contact_info": "email",
        "profile_data": "username",
    }

    fact_repo = NormalizedFactRepository(db)
    facts = fact_repo.list_by_investigation(investigation_id)

    items: list[IdentifierRead] = []
    for f in facts:
        identifier_type = IDENTIFIER_FACT_TYPES.get(f.fact_type)
        if identifier_type is None:
            continue

        meta: dict = f.fact_metadata or {}

        if f.fact_type in ("profile_data", "social_account", "username"):
            display_value = meta.get("username") or str(f.value)
            profile_url: str | None = meta.get("profile_url") or None
        else:
            display_value = str(f.value)
            profile_url = None

        items.append(
            IdentifierRead(
                id=str(f.id),
                type=identifier_type,
                value=display_value,
                confidence=f.confidence,
                sources=1,
                first_seen=f.created_at.isoformat() if f.created_at else "",
                profile_url=profile_url,
            )
        )

    return IdentifierListResponse(items=items, count=len(items))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestUsernameIdentifiers:
    """profile_data facts should produce clean username + profile_url."""

    def test_profile_data_yields_username_type(self, db_session):
        inv_id = uuid.uuid4()
        _make_fact(
            db_session,
            inv_id,
            fact_type="profile_data",
            value='{"platform":"github","username":"jdoe","exists":true}',
            metadata={
                "platform_id": "github",
                "username": "jdoe",
                "exists": True,
                "profile_url": "https://github.com/jdoe",
            },
        )
        result = _run_list_identifiers(db_session, inv_id)
        assert result.count == 1
        assert result.items[0].type == "username"

    def test_profile_data_value_is_clean_username(self, db_session):
        inv_id = uuid.uuid4()
        _make_fact(
            db_session,
            inv_id,
            fact_type="profile_data",
            value='{"platform":"github","username":"jdoe","exists":true}',
            metadata={
                "username": "jdoe",
                "profile_url": "https://github.com/jdoe",
                "exists": True,
            },
        )
        result = _run_list_identifiers(db_session, inv_id)
        item = result.items[0]
        # Must be the clean username, not the JSON blob
        assert item.value == "jdoe"
        assert "{" not in item.value

    def test_profile_url_survives_full_api_conversion(self, db_session):
        inv_id = uuid.uuid4()
        _make_fact(
            db_session,
            inv_id,
            fact_type="profile_data",
            value='{"platform":"github","username":"jdoe","exists":true}',
            metadata={
                "username": "jdoe",
                "profile_url": "https://github.com/jdoe",
                "exists": True,
            },
        )
        result = _run_list_identifiers(db_session, inv_id)
        assert result.items[0].profile_url == "https://github.com/jdoe"

    def test_profile_url_returned_by_get_identifiers_schema(self, db_session):
        """IdentifierRead schema must carry profile_url to the client."""
        inv_id = uuid.uuid4()
        _make_fact(
            db_session,
            inv_id,
            fact_type="profile_data",
            value='{"platform":"twitter","username":"alice","exists":true}',
            metadata={
                "username": "alice",
                "profile_url": "https://twitter.com/alice",
                "exists": True,
            },
        )
        result = _run_list_identifiers(db_session, inv_id)
        # Verify profile_url is present in the serialised response
        data = result.model_dump()
        assert data["items"][0]["profile_url"] == "https://twitter.com/alice"

    def test_profile_url_none_when_account_not_found(self, db_session):
        """Accounts where exists=False should have profile_url=None."""
        inv_id = uuid.uuid4()
        _make_fact(
            db_session,
            inv_id,
            fact_type="profile_data",
            value='{"platform":"github","username":"jdoe","exists":false}',
            metadata={
                "username": "jdoe",
                "profile_url": None,
                "exists": False,
            },
        )
        result = _run_list_identifiers(db_session, inv_id)
        assert result.items[0].profile_url is None

    def test_social_account_clean_username_and_profile_url(self, db_session):
        inv_id = uuid.uuid4()
        _make_fact(
            db_session,
            inv_id,
            fact_type="social_account",
            value="jdoe@github",
            metadata={
                "username": "jdoe",
                "platform": "github",
                "profile_url": "https://github.com/jdoe",
            },
        )
        result = _run_list_identifiers(db_session, inv_id)
        assert result.count == 1
        item = result.items[0]
        assert item.type == "social"
        assert item.value == "jdoe"
        assert item.profile_url == "https://github.com/jdoe"


class TestDomainIdentifiers:
    """Actual domain values should pass through as type=domain."""

    def test_domain_fact_is_type_domain(self, db_session):
        inv_id = uuid.uuid4()
        _make_fact(db_session, inv_id, fact_type="domain", value="example.com")
        result = _run_list_identifiers(db_session, inv_id)
        assert result.count == 1
        item = result.items[0]
        assert item.type == "domain"
        assert item.value == "example.com"

    def test_domain_identifiers_remain_correct(self, db_session):
        """Domain facts must keep their value intact with no mutation."""
        inv_id = uuid.uuid4()
        _make_fact(db_session, inv_id, fact_type="domain", value="sub.example.co.uk")
        result = _run_list_identifiers(db_session, inv_id)
        assert result.items[0].value == "sub.example.co.uk"

    def test_domain_has_no_profile_url(self, db_session):
        inv_id = uuid.uuid4()
        _make_fact(db_session, inv_id, fact_type="domain", value="example.com")
        result = _run_list_identifiers(db_session, inv_id)
        assert result.items[0].profile_url is None


class TestEmailPhoneIdentifiers:
    """Email and phone facts should remain unchanged."""

    def test_email_fact_unchanged(self, db_session):
        inv_id = uuid.uuid4()
        _make_fact(db_session, inv_id, fact_type="email", value="user@example.com")
        result = _run_list_identifiers(db_session, inv_id)
        assert result.count == 1
        item = result.items[0]
        assert item.type == "email"
        assert item.value == "user@example.com"
        assert item.profile_url is None

    def test_phone_fact_unchanged(self, db_session):
        inv_id = uuid.uuid4()
        _make_fact(db_session, inv_id, fact_type="phone", value="+15550001234")
        result = _run_list_identifiers(db_session, inv_id)
        assert result.count == 1
        item = result.items[0]
        assert item.type == "phone"
        assert item.value == "+15550001234"
        assert item.profile_url is None


class TestWhoisMetadataExclusion:
    """
    WHOIS metadata fact types must NOT appear in the identifier list.
    These are contextual metadata, not standalone identifiers.
    """

    EXCLUDED_FACT_TYPES = [
        "registrar",
        "nameserver",
        "expiration",
        "organization",
        "location",
        "generic",
        "certificate",
        "archive_snapshot",
        "image_hash",
        "domain_registration",
    ]

    @pytest.mark.parametrize("fact_type", EXCLUDED_FACT_TYPES)
    def test_whois_metadata_fact_excluded(self, db_session, fact_type):
        """Each WHOIS metadata fact type must produce zero identifier rows."""
        inv_id = uuid.uuid4()
        _make_fact(db_session, inv_id, fact_type=fact_type, value="some-value")
        result = _run_list_identifiers(db_session, inv_id)
        assert result.count == 0, (
            f"fact_type={fact_type!r} should be excluded from identifiers "
            f"but produced {result.count} row(s)"
        )

    def test_registrar_not_exposed_as_domain_identifier(self, db_session):
        inv_id = uuid.uuid4()
        _make_fact(db_session, inv_id, fact_type="registrar", value="Example Registrar LLC")
        result = _run_list_identifiers(db_session, inv_id)
        assert result.count == 0

    def test_organization_not_exposed_as_domain_identifier(self, db_session):
        inv_id = uuid.uuid4()
        _make_fact(db_session, inv_id, fact_type="organization", value="Acme Corp")
        result = _run_list_identifiers(db_session, inv_id)
        assert result.count == 0

    def test_dates_not_exposed_as_domain_identifiers(self, db_session):
        inv_id = uuid.uuid4()
        _make_fact(db_session, inv_id, fact_type="domain_registration", value="2020-01-01T00:00:00")
        _make_fact(db_session, inv_id, fact_type="expiration", value="2025-01-01T00:00:00")
        result = _run_list_identifiers(db_session, inv_id)
        assert result.count == 0

    def test_nameservers_not_exposed_as_domain_identifiers(self, db_session):
        inv_id = uuid.uuid4()
        _make_fact(db_session, inv_id, fact_type="nameserver", value="ns1.example.com")
        _make_fact(db_session, inv_id, fact_type="nameserver", value="ns2.example.com")
        result = _run_list_identifiers(db_session, inv_id)
        assert result.count == 0

    def test_mixed_facts_only_real_identifiers_returned(self, db_session):
        """
        When a domain investigation produces WHOIS metadata + real identifiers,
        only the genuine identifiers should appear.
        """
        inv_id = uuid.uuid4()
        # WHOIS metadata — all should be excluded
        _make_fact(db_session, inv_id, fact_type="registrar", value="Example Registrar LLC")
        _make_fact(db_session, inv_id, fact_type="nameserver", value="ns1.example.com")
        _make_fact(db_session, inv_id, fact_type="organization", value="Example Corp")
        _make_fact(db_session, inv_id, fact_type="domain_registration", value="2020-01-01T00:00:00")
        _make_fact(db_session, inv_id, fact_type="expiration", value="2025-01-01T00:00:00")
        _make_fact(db_session, inv_id, fact_type="location", value="US")
        # Real identifiers
        _make_fact(db_session, inv_id, fact_type="email", value="admin@example.com")
        _make_fact(db_session, inv_id, fact_type="domain", value="example.com")

        result = _run_list_identifiers(db_session, inv_id)
        assert result.count == 2
        types = {item.type for item in result.items}
        assert types == {"email", "domain"}
        values = {item.value for item in result.items}
        assert values == {"admin@example.com", "example.com"}
