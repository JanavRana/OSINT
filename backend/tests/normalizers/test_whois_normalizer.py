from datetime import datetime

import pytest

from app.normalizers.whois import WhoisNormalizer


@pytest.fixture
def normalizer():
    return WhoisNormalizer()


def test_normalize_full_whois_data(normalizer):
    raw_payload = {
        "registrar": "Example Registrar Inc.",
        "creation_date": datetime(2020, 1, 15, 10, 30, 0),
        "expiration_date": datetime(2025, 1, 15, 10, 30, 0),
        "name_servers": ["ns1.example.com", "ns2.example.com"],
        "org": "Example Organization",
        "country": "US",
    }

    facts = normalizer.normalize(raw_payload)

    assert len(facts) == 7
    
    fact_types = {fact.fact_type for fact in facts}
    assert "registrar" in fact_types
    assert "domain_registration" in fact_types
    assert "domain_expiration" in fact_types
    assert "nameserver" in fact_types
    assert "registrant_organization" in fact_types
    assert "registrant_country" in fact_types

    registrar_fact = next(f for f in facts if f.fact_type == "registrar")
    assert registrar_fact.value == "Example Registrar Inc."

    registration_fact = next(f for f in facts if f.fact_type == "domain_registration")
    assert registration_fact.occurred_at == datetime(2020, 1, 15, 10, 30, 0)
    assert registration_fact.attributes["creation_date"] == "2020-01-15T10:30:00"

    expiration_fact = next(f for f in facts if f.fact_type == "domain_expiration")
    assert expiration_fact.occurred_at == datetime(2025, 1, 15, 10, 30, 0)

    ns_facts = [f for f in facts if f.fact_type == "nameserver"]
    assert len(ns_facts) == 2
    ns_values = {f.value for f in ns_facts}
    assert "ns1.example.com" in ns_values
    assert "ns2.example.com" in ns_values

    org_fact = next(f for f in facts if f.fact_type == "registrant_organization")
    assert org_fact.value == "Example Organization"

    country_fact = next(f for f in facts if f.fact_type == "registrant_country")
    assert country_fact.value == "US"


def test_normalize_list_values(normalizer):
    raw_payload = {
        "registrar": ["Registrar 1", "Registrar 2"],
        "creation_date": [datetime(2020, 1, 15), datetime(2020, 1, 15)],
        "org": ["Org 1", "Org 2"],
        "country": ["US", "CA"],
    }

    facts = normalizer.normalize(raw_payload)

    registrar_fact = next(f for f in facts if f.fact_type == "registrar")
    assert registrar_fact.value == "Registrar 1"

    org_fact = next(f for f in facts if f.fact_type == "registrant_organization")
    assert org_fact.value == "Org 1"

    country_fact = next(f for f in facts if f.fact_type == "registrant_country")
    assert country_fact.value == "US"


def test_normalize_iso_date_strings(normalizer):
    raw_payload = {
        "creation_date": "2020-01-15T10:30:00",
        "expiration_date": "2025-01-15T10:30:00Z",
    }

    facts = normalizer.normalize(raw_payload)

    registration_fact = next(f for f in facts if f.fact_type == "domain_registration")
    assert registration_fact.occurred_at is not None
    assert registration_fact.occurred_at.year == 2020
    assert registration_fact.occurred_at.month == 1
    assert registration_fact.occurred_at.day == 15


def test_normalize_missing_fields(normalizer):
    raw_payload = {
        "registrar": "Example Registrar",
    }

    facts = normalizer.normalize(raw_payload)

    assert len(facts) == 1
    assert facts[0].fact_type == "registrar"


def test_normalize_empty_payload(normalizer):
    raw_payload = {}

    facts = normalizer.normalize(raw_payload)

    assert len(facts) == 0


def test_normalize_whitespace_handling(normalizer):
    raw_payload = {
        "registrar": "  Example Registrar  ",
        "org": "  Example Org  ",
        "country": "  US  ",
    }

    facts = normalizer.normalize(raw_payload)

    registrar_fact = next(f for f in facts if f.fact_type == "registrar")
    assert registrar_fact.value == "Example Registrar"

    org_fact = next(f for f in facts if f.fact_type == "registrant_organization")
    assert org_fact.value == "Example Org"

    country_fact = next(f for f in facts if f.fact_type == "registrant_country")
    assert country_fact.value == "US"


def test_normalize_empty_strings(normalizer):
    raw_payload = {
        "registrar": "",
        "org": "   ",
        "country": "",
    }

    facts = normalizer.normalize(raw_payload)

    assert len(facts) == 0


def test_nameserver_deduplication(normalizer):
    raw_payload = {
        "name_servers": ["NS1.EXAMPLE.COM", "ns1.example.com", "ns2.example.com"],
    }

    facts = normalizer.normalize(raw_payload)

    ns_facts = [f for f in facts if f.fact_type == "nameserver"]
    assert len(ns_facts) == 2
    ns_values = {f.value for f in ns_facts}
    assert "ns1.example.com" in ns_values
    assert "ns2.example.com" in ns_values


def test_nameserver_single_string(normalizer):
    raw_payload = {
        "name_servers": "ns1.example.com",
    }

    facts = normalizer.normalize(raw_payload)

    ns_facts = [f for f in facts if f.fact_type == "nameserver"]
    assert len(ns_facts) == 1
    assert ns_facts[0].value == "ns1.example.com"
