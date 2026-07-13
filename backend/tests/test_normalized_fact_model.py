"""Tests for NormalizedFact model."""

import uuid
from datetime import datetime, timezone

from app.models.normalized_fact import NormalizedFact


def test_normalized_fact_instantiation():
    """Test that NormalizedFact can be instantiated with required fields."""
    investigation_id = uuid.uuid4()
    occurred_at = datetime.now(timezone.utc)
    
    fact = NormalizedFact(
        investigation_id=investigation_id,
        connector_name="whois",
        fact_type="domain_registration",
        value="example.com",
        confidence=0.95,
        fact_metadata={"source": "whois"},
        occurred_at=occurred_at,
    )
    
    assert fact.investigation_id == investigation_id
    assert fact.connector_name == "whois"
    assert fact.fact_type == "domain_registration"
    assert fact.value == "example.com"
    assert fact.confidence == 0.95
    assert fact.fact_metadata == {"source": "whois"}
    assert fact.occurred_at == occurred_at


if __name__ == "__main__":
    test_normalized_fact_instantiation()
    print("All tests passed!")
