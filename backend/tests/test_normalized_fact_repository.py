"""Tests for NormalizedFactRepository."""

import os
import uuid
from datetime import datetime, timezone

# Set test database URL before importing anything else
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.session import Base
from app.models.investigation import Investigation, InvestigationStatus
from app.models.normalized_fact import NormalizedFact
from app.repositories.normalized_fact_repository import NormalizedFactRepository


def setup_test_db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_create_normalized_fact():
    """Test creating a normalized fact."""
    db = setup_test_db()
    
    # Create a test investigation first
    investigation = Investigation(
        name="Test Investigation",
        status=InvestigationStatus.CREATED,
    )
    db.add(investigation)
    db.commit()
    db.refresh(investigation)
    
    # Create repository and normalized fact
    repo = NormalizedFactRepository(db)
    occurred_at = datetime.now(timezone.utc)
    
    fact = repo.create(
        investigation_id=investigation.id,
        connector_name="whois",
        fact_type="domain_registration",
        value="example.com",
        confidence=0.95,
        fact_metadata={"source": "whois", "raw_data": "test"},
        occurred_at=occurred_at,
    )
    
    assert fact.id is not None
    assert fact.investigation_id == investigation.id
    assert fact.connector_name == "whois"
    assert fact.fact_type == "domain_registration"
    assert fact.value == "example.com"
    assert fact.confidence == 0.95
    assert fact.fact_metadata == {"source": "whois", "raw_data": "test"}
    # SQLite may strip timezone info, so compare timestamps loosely
    assert abs((fact.occurred_at.replace(tzinfo=None) - occurred_at.replace(tzinfo=None)).total_seconds()) < 2
    assert fact.created_at is not None
    
    db.close()


if __name__ == "__main__":
    test_create_normalized_fact()
    print("All tests passed!")
