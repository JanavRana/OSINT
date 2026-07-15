"""
Tests for TimelineService.
"""

import os
import uuid
from datetime import datetime

# Set test database URL before importing anything else
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.session import Base
from app.models.investigation import Investigation, InvestigationStatus
from app.models.normalized_fact import NormalizedFact
from app.timeline.service import TimelineService


def setup_test_db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_empty_timeline():
    """Test timeline with no facts."""
    db = setup_test_db()
    investigation = Investigation(
        name="Test Investigation",
        status=InvestigationStatus.CREATED,
    )
    db.add(investigation)
    db.commit()
    db.refresh(investigation)
    
    timeline_service = TimelineService(db)
    events = timeline_service.get_timeline(investigation.id)
    assert events == []
    db.close()


def test_whois_events():
    """Test extraction of WHOIS events."""
    db = setup_test_db()
    investigation = Investigation(
        name="Test Investigation",
        status=InvestigationStatus.CREATED,
    )
    db.add(investigation)
    db.commit()
    db.refresh(investigation)
    
    fact = NormalizedFact(
        investigation_id=investigation.id,
        connector_name="whois",
        fact_type="domain",
        value="example.com",
        confidence=0.95,
        fact_metadata={
            "registration_date": "2020-01-15T10:00:00Z",
            "expiration_date": "2025-01-15T10:00:00Z",
            "updated_date": "2023-06-01T15:30:00Z",
        },
        occurred_at=datetime(2020, 1, 15, 10, 0, 0),
    )
    db.add(fact)
    db.commit()

    timeline_service = TimelineService(db)
    events = timeline_service.get_timeline(investigation.id)

    assert len(events) == 3
    assert events[0].event_type == "registration"
    assert events[0].title == "Domain example.com registered"
    assert events[0].connector == "whois"
    assert events[0].confidence == 0.95
    assert events[1].event_type == "updated"
    assert events[2].event_type == "expiration"
    db.close()


def test_rdap_events():
    """Test extraction of RDAP events."""
    db = setup_test_db()
    investigation = Investigation(
        name="Test Investigation",
        status=InvestigationStatus.CREATED,
    )
    db.add(investigation)
    db.commit()
    db.refresh(investigation)
    
    fact = NormalizedFact(
        investigation_id=investigation.id,
        connector_name="rdap",
        fact_type="domain",
        value="example.org",
        confidence=0.90,
        fact_metadata={
            "registration_date": "2019-03-20T08:00:00Z",
            "expiration_date": "2024-03-20T08:00:00Z",
            "last_changed": "2022-11-10T12:00:00Z",
        },
        occurred_at=datetime(2019, 3, 20, 8, 0, 0),
    )
    db.add(fact)
    db.commit()

    timeline_service = TimelineService(db)
    events = timeline_service.get_timeline(investigation.id)

    assert len(events) == 3
    assert events[0].event_type == "registration"
    assert events[0].connector == "rdap"
    assert events[1].event_type == "last_changed"
    assert events[2].event_type == "expiration"
    db.close()


def test_crtsh_events():
    """Test extraction of crt.sh events."""
    db = setup_test_db()
    investigation = Investigation(
        name="Test Investigation",
        status=InvestigationStatus.CREATED,
    )
    db.add(investigation)
    db.commit()
    db.refresh(investigation)
    
    fact = NormalizedFact(
        investigation_id=investigation.id,
        connector_name="crt.sh",
        fact_type="certificate",
        value="*.example.com",
        confidence=1.0,
        fact_metadata={
            "not_before": "2023-01-01T00:00:00Z",
            "not_after": "2024-01-01T00:00:00Z",
        },
        occurred_at=datetime(2023, 1, 1, 0, 0, 0),
    )
    db.add(fact)
    db.commit()

    timeline_service = TimelineService(db)
    events = timeline_service.get_timeline(investigation.id)

    assert len(events) == 2
    assert events[0].event_type == "certificate_issued"
    assert events[0].title == "Certificate issued for *.example.com"
    assert events[1].event_type == "certificate_expires"
    db.close()


def test_wayback_events():
    """Test extraction of Wayback events."""
    db = setup_test_db()
    investigation = Investigation(
        name="Test Investigation",
        status=InvestigationStatus.CREATED,
    )
    db.add(investigation)
    db.commit()
    db.refresh(investigation)
    
    fact = NormalizedFact(
        investigation_id=investigation.id,
        connector_name="wayback",
        fact_type="snapshot",
        value="example.com",
        confidence=0.85,
        fact_metadata={
            "timestamp": "2018-07-15T14:30:00Z",
        },
        occurred_at=datetime(2018, 7, 15, 14, 30, 0),
    )
    db.add(fact)
    db.commit()

    timeline_service = TimelineService(db)
    events = timeline_service.get_timeline(investigation.id)

    assert len(events) == 1
    assert events[0].event_type == "archive_snapshot"
    assert events[0].title == "Archive snapshot of example.com"
    db.close()


def test_chronological_sorting():
    """Test that events are sorted chronologically."""
    db = setup_test_db()
    investigation = Investigation(
        name="Test Investigation",
        status=InvestigationStatus.CREATED,
    )
    db.add(investigation)
    db.commit()
    db.refresh(investigation)
    
    fact1 = NormalizedFact(
        investigation_id=investigation.id,
        connector_name="whois",
        fact_type="domain",
        value="example.com",
        confidence=0.95,
        fact_metadata={
            "registration_date": "2022-01-01T00:00:00Z",
        },
        occurred_at=datetime(2022, 1, 1, 0, 0, 0),
    )
    fact2 = NormalizedFact(
        investigation_id=investigation.id,
        connector_name="whois",
        fact_type="domain",
        value="example.com",
        confidence=0.95,
        fact_metadata={
            "expiration_date": "2020-01-01T00:00:00Z",
        },
        occurred_at=datetime(2020, 1, 1, 0, 0, 0),
    )
    db.add_all([fact1, fact2])
    db.commit()

    timeline_service = TimelineService(db)
    events = timeline_service.get_timeline(investigation.id)

    assert len(events) == 2
    assert events[0].occurred_at < events[1].occurred_at
    assert events[0].event_type == "expiration"
    assert events[1].event_type == "registration"
    db.close()


def test_duplicate_removal():
    """Test that duplicate events are removed."""
    db = setup_test_db()
    investigation = Investigation(
        name="Test Investigation",
        status=InvestigationStatus.CREATED,
    )
    db.add(investigation)
    db.commit()
    db.refresh(investigation)
    
    # Create two facts with same event data
    fact1 = NormalizedFact(
        investigation_id=investigation.id,
        connector_name="whois",
        fact_type="domain",
        value="example.com",
        confidence=0.95,
        fact_metadata={
            "registration_date": "2020-01-01T00:00:00Z",
        },
        occurred_at=datetime(2020, 1, 1, 0, 0, 0),
    )
    fact2 = NormalizedFact(
        investigation_id=investigation.id,
        connector_name="rdap",
        fact_type="domain",
        value="example.com",
        confidence=0.90,
        fact_metadata={
            "registration_date": "2020-01-01T00:00:00Z",
        },
        occurred_at=datetime(2020, 1, 1, 0, 0, 0),
    )
    db.add_all([fact1, fact2])
    db.commit()

    timeline_service = TimelineService(db)
    events = timeline_service.get_timeline(investigation.id)

    # Should only have 1 event (duplicate registration removed)
    assert len(events) == 1
    db.close()


def test_filter_by_entity_id():
    """Test filtering events by entity_id."""
    db = setup_test_db()
    investigation = Investigation(
        name="Test Investigation",
        status=InvestigationStatus.CREATED,
    )
    db.add(investigation)
    db.commit()
    db.refresh(investigation)
    
    fact1 = NormalizedFact(
        investigation_id=investigation.id,
        connector_name="whois",
        fact_type="domain",
        value="example.com",
        confidence=0.95,
        fact_metadata={
            "registration_date": "2020-01-01T00:00:00Z",
        },
        occurred_at=datetime(2020, 1, 1, 0, 0, 0),
    )
    fact2 = NormalizedFact(
        investigation_id=investigation.id,
        connector_name="whois",
        fact_type="domain",
        value="other.com",
        confidence=0.95,
        fact_metadata={
            "registration_date": "2021-01-01T00:00:00Z",
        },
        occurred_at=datetime(2021, 1, 1, 0, 0, 0),
    )
    db.add_all([fact1, fact2])
    db.commit()

    timeline_service = TimelineService(db)
    events = timeline_service.get_timeline(
        investigation.id, entity_id="example.com"
    )

    assert len(events) == 1
    assert events[0].entity_id == "example.com"
    db.close()


def test_filter_by_event_type():
    """Test filtering events by event_type."""
    db = setup_test_db()
    investigation = Investigation(
        name="Test Investigation",
        status=InvestigationStatus.CREATED,
    )
    db.add(investigation)
    db.commit()
    db.refresh(investigation)
    
    fact = NormalizedFact(
        investigation_id=investigation.id,
        connector_name="whois",
        fact_type="domain",
        value="example.com",
        confidence=0.95,
        fact_metadata={
            "registration_date": "2020-01-01T00:00:00Z",
            "expiration_date": "2025-01-01T00:00:00Z",
        },
        occurred_at=datetime(2020, 1, 1, 0, 0, 0),
    )
    db.add(fact)
    db.commit()

    timeline_service = TimelineService(db)
    events = timeline_service.get_timeline(
        investigation.id, event_type="registration"
    )

    assert len(events) == 1
    assert events[0].event_type == "registration"
    db.close()


def test_ignore_facts_without_timestamps():
    """Test that facts without timestamps in metadata are ignored."""
    db = setup_test_db()
    investigation = Investigation(
        name="Test Investigation",
        status=InvestigationStatus.CREATED,
    )
    db.add(investigation)
    db.commit()
    db.refresh(investigation)
    
    fact = NormalizedFact(
        investigation_id=investigation.id,
        connector_name="whois",
        fact_type="domain",
        value="example.com",
        confidence=0.95,
        fact_metadata={
            "registrar": "Example Registrar",
            "status": "active",
        },
        occurred_at=datetime(2020, 1, 1, 0, 0, 0),
    )
    db.add(fact)
    db.commit()

    timeline_service = TimelineService(db)
    events = timeline_service.get_timeline(investigation.id)

    assert len(events) == 0
    db.close()


def test_generic_timestamp_extraction():
    """Test that generic timestamp fields are extracted for unknown connectors."""
    db = setup_test_db()
    investigation = Investigation(
        name="Test Investigation",
        status=InvestigationStatus.CREATED,
    )
    db.add(investigation)
    db.commit()
    db.refresh(investigation)
    
    fact = NormalizedFact(
        investigation_id=investigation.id,
        connector_name="future_connector",
        fact_type="generic_event",
        value="test.com",
        confidence=0.80,
        fact_metadata={
            "timestamp": "2023-05-10T12:00:00Z",
            "some_other_field": "value",
        },
        occurred_at=datetime(2023, 5, 10, 12, 0, 0),
    )
    db.add(fact)
    db.commit()

    timeline_service = TimelineService(db)
    events = timeline_service.get_timeline(investigation.id)

    assert len(events) == 1
    assert events[0].event_type == "generic_event"
    assert events[0].connector == "future_connector"
    db.close()


if __name__ == "__main__":
    test_empty_timeline()
    test_whois_events()
    test_rdap_events()
    test_crtsh_events()
    test_wayback_events()
    test_chronological_sorting()
    test_duplicate_removal()
    test_filter_by_entity_id()
    test_filter_by_event_type()
    test_ignore_facts_without_timestamps()
    test_generic_timestamp_extraction()
    print("All tests passed!")
