from datetime import datetime

import pytest

from app.correlation.engine import CorrelationEngine
from app.normalizers.types import FactType, NormalizedFact


@pytest.fixture
def engine():
    return CorrelationEngine()


@pytest.fixture
def sample_facts():
    return [
        NormalizedFact(
            fact_type=FactType.DOMAIN,
            value="example.com",
            source_connector="whois",
            confidence=1.0,
            metadata={"field": "domain"}
        ),
        NormalizedFact(
            fact_type=FactType.GENERIC,
            value="Example Registrar",
            source_connector="whois",
            confidence=1.0,
            metadata={"field": "registrar"}
        ),
        NormalizedFact(
            fact_type=FactType.ORGANIZATION,
            value="Example Org",
            source_connector="whois",
            confidence=1.0,
            metadata={"field": "registrant_organization"}
        ),
        NormalizedFact(
            fact_type=FactType.GENERIC,
            value="ns1.example.com",
            source_connector="whois",
            confidence=1.0,
            metadata={"field": "nameserver"}
        ),
        NormalizedFact(
            fact_type=FactType.LOCATION,
            value="US",
            source_connector="whois",
            confidence=1.0,
            metadata={"field": "registrant_country"}
        ),
    ]


def test_correlate_empty_facts(engine):
    result = engine.correlate([])
    assert len(result.entities) == 0
    assert len(result.relationships) == 0


def test_correlate_single_fact(engine):
    facts = [
        NormalizedFact(
            fact_type=FactType.DOMAIN,
            value="example.com",
            source_connector="whois",
            confidence=1.0,
            metadata={}
        )
    ]
    result = engine.correlate(facts)
    assert len(result.entities) == 1
    assert result.entities[0].entity_type == "domain"
    assert result.entities[0].primary_value == "example.com"


def test_correlate_duplicate_detection(engine):
    facts = [
        NormalizedFact(
            fact_type=FactType.GENERIC,
            value="Example Registrar",
            source_connector="whois",
            confidence=1.0,
            metadata={"field": "registrar"}
        ),
        NormalizedFact(
            fact_type=FactType.GENERIC,
            value="Example Registrar",
            source_connector="rdap",
            confidence=1.0,
            metadata={"field": "registrar"}
        ),
    ]
    result = engine.correlate(facts)
    
    registrar_entities = [e for e in result.entities if e.entity_type == "registrar"]
    assert len(registrar_entities) == 1
    assert len(registrar_entities[0].evidence) == 2


def test_correlate_with_relationships(engine, sample_facts):
    result = engine.correlate(sample_facts)
    
    assert len(result.entities) > 0
    
    domain_entities = [e for e in result.entities if e.entity_type == "domain"]
    assert len(domain_entities) == 1
    
    registrar_entities = [e for e in result.entities if e.entity_type == "registrar"]
    assert len(registrar_entities) == 1


def test_confidence_scoring(engine):
    facts = [
        NormalizedFact(
            fact_type=FactType.DOMAIN,
            value="example.com",
            source_connector="whois",
            confidence=0.9,
            metadata={}
        ),
        NormalizedFact(
            fact_type=FactType.GENERIC,
            value="Example Registrar",
            source_connector="whois",
            confidence=0.8,
            metadata={"field": "registrar"}
        ),
    ]
    result = engine.correlate(facts)
    
    for entity in result.entities:
        assert 0.0 <= entity.confidence <= 1.0


def test_evidence_collection(engine, sample_facts):
    result = engine.correlate(sample_facts)
    
    for entity in result.entities:
        assert len(entity.evidence) > 0
        for evidence in entity.evidence:
            assert evidence.source_connector is not None


def test_deterministic_results(engine, sample_facts):
    result1 = engine.correlate(sample_facts)
    
    engine2 = CorrelationEngine()
    result2 = engine2.correlate(sample_facts)
    
    assert len(result1.entities) == len(result2.entities)
    assert len(result1.relationships) == len(result2.relationships)


def test_entity_types(engine, sample_facts):
    result = engine.correlate(sample_facts)
    
    entity_types = {e.entity_type for e in result.entities}
    expected_types = {"domain", "registrar", "organization", "nameserver", "country"}
    assert entity_types == expected_types


def test_relationship_types(engine, sample_facts):
    result = engine.correlate(sample_facts)
    
    relationship_types = {r.relationship_type for r in result.relationships}
    expected_types = {"registered_with", "owned_by", "uses_nameserver", "registered_in"}
    assert relationship_types.issubset(expected_types)


def test_no_duplicate_entities(engine):
    facts = [
        NormalizedFact(
            fact_type=FactType.GENERIC,
            value="ns1.example.com",
            source_connector="whois",
            confidence=1.0,
            metadata={"field": "nameserver"}
        ),
        NormalizedFact(
            fact_type=FactType.GENERIC,
            value="ns1.example.com",
            source_connector="whois",
            confidence=1.0,
            metadata={"field": "nameserver"}
        ),
    ]
    result = engine.correlate(facts)
    
    ns_entities = [e for e in result.entities if e.entity_type == "nameserver"]
    assert len(ns_entities) == 1


def test_metadata_preservation(engine):
    facts = [
        NormalizedFact(
            fact_type=FactType.DOMAIN_REGISTRATION,
            value="2020-01-01",
            source_connector="whois",
            confidence=1.0,
            occurred_at=datetime(2020, 1, 1),
            metadata={"field": "creation_date"}
        ),
    ]
    result = engine.correlate(facts)
    
    assert len(result.entities) > 0
    entity = result.entities[0]
    assert len(entity.evidence) > 0
    assert entity.evidence[0].occurred_at is not None
