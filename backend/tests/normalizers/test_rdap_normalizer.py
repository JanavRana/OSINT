"""Tests for RdapNormalizer."""

from datetime import datetime

import pytest

from app.normalizers.rdap import RdapNormalizer
from app.normalizers.types import FactType, NormalizationError


@pytest.fixture
def normalizer():
    return RdapNormalizer()


def test_normalize_full_rdap_data(normalizer):
    """Test normalization of a complete RDAP response."""
    raw_payload = {
        "ldhName": "example.com",
        "events": [
            {
                "eventAction": "registration",
                "eventDate": "2020-01-15T10:30:00Z",
            },
            {
                "eventAction": "expiration",
                "eventDate": "2025-01-15T10:30:00Z",
            },
        ],
        "nameservers": [
            {"ldhName": "ns1.example.com"},
            {"ldhName": "ns2.example.com"},
        ],
        "entities": [
            {
                "roles": ["registrar"],
                "vcardArray": [
                    "vcard",
                    [
                        ["fn", {}, "text", "Example Registrar Inc."],
                        ["email", {}, "text", "contact@registrar.example"],
                    ],
                ],
            },
        ],
    }

    facts = normalizer.normalize(raw_payload)

    assert len(facts) > 0

    # Check domain fact
    domain_facts = [f for f in facts if f.fact_type == FactType.DOMAIN]
    assert len(domain_facts) == 1
    assert domain_facts[0].value == "example.com"

    # Check registration date
    registration_facts = [
        f for f in facts if f.fact_type == FactType.DOMAIN_REGISTRATION
    ]
    assert len(registration_facts) == 1
    assert registration_facts[0].occurred_at.year == 2020

    # Check expiration date
    expiration_facts = [f for f in facts if f.fact_type == FactType.EXPIRATION]
    assert len(expiration_facts) == 1
    assert expiration_facts[0].occurred_at.year == 2025

    # Check nameservers
    ns_facts = [f for f in facts if f.fact_type == FactType.NAMESERVER]
    assert len(ns_facts) == 2
    ns_values = {f.value for f in ns_facts}
    assert "ns1.example.com" in ns_values
    assert "ns2.example.com" in ns_values

    # Check registrar
    registrar_facts = [f for f in facts if f.fact_type == FactType.REGISTRAR]
    assert len(registrar_facts) == 1
    assert registrar_facts[0].value == "Example Registrar Inc."

    # Check email
    email_facts = [f for f in facts if f.fact_type == FactType.EMAIL]
    assert len(email_facts) == 1
    assert email_facts[0].value == "contact@registrar.example"


def test_normalize_with_unicode_name(normalizer):
    """Test normalization with unicode domain name."""
    raw_payload = {
        "unicodeName": "example.com",
        "events": [],
        "nameservers": [],
        "entities": [],
    }

    facts = normalizer.normalize(raw_payload)

    domain_facts = [f for f in facts if f.fact_type == FactType.DOMAIN]
    assert len(domain_facts) == 1
    assert domain_facts[0].value == "example.com"


def test_normalize_nameserver_deduplication(normalizer):
    """Test that duplicate nameservers are deduplicated."""
    raw_payload = {
        "ldhName": "example.com",
        "nameservers": [
            {"ldhName": "NS1.EXAMPLE.COM"},
            {"ldhName": "ns1.example.com"},
            {"ldhName": "ns2.example.com"},
        ],
    }

    facts = normalizer.normalize(raw_payload)

    ns_facts = [f for f in facts if f.fact_type == FactType.NAMESERVER]
    assert len(ns_facts) == 2
    ns_values = {f.value for f in ns_facts}
    assert "ns1.example.com" in ns_values
    assert "ns2.example.com" in ns_values


def test_normalize_entity_with_org(normalizer):
    """Test extraction of organization from entity."""
    raw_payload = {
        "ldhName": "example.com",
        "entities": [
            {
                "roles": ["administrative"],
                "vcardArray": [
                    "vcard",
                    [
                        ["org", {}, "text", ["Example Organization", "Division"]],
                        ["email", {}, "text", "admin@example.com"],
                        ["tel", {}, "text", "+1-555-0100"],
                    ],
                ],
            },
        ],
    }

    facts = normalizer.normalize(raw_payload)

    # Check organization
    org_facts = [f for f in facts if f.fact_type == FactType.ORGANIZATION]
    assert len(org_facts) == 1
    assert org_facts[0].value == "Example Organization"

    # Check email
    email_facts = [f for f in facts if f.fact_type == FactType.EMAIL]
    assert len(email_facts) == 1
    assert email_facts[0].value == "admin@example.com"

    # Check phone
    phone_facts = [f for f in facts if f.fact_type == FactType.PHONE]
    assert len(phone_facts) == 1
    assert phone_facts[0].value == "+1-555-0100"


def test_normalize_nested_entities(normalizer):
    """Test extraction from nested entities."""
    raw_payload = {
        "ldhName": "example.com",
        "entities": [
            {
                "roles": ["registrar"],
                "vcardArray": [
                    "vcard",
                    [["fn", {}, "text", "Example Registrar"]],
                ],
                "entities": [
                    {
                        "roles": ["technical"],
                        "vcardArray": [
                            "vcard",
                            [["email", {}, "text", "tech@registrar.example"]],
                        ],
                    },
                ],
            },
        ],
    }

    facts = normalizer.normalize(raw_payload)

    # Check registrar
    registrar_facts = [f for f in facts if f.fact_type == FactType.REGISTRAR]
    assert len(registrar_facts) == 1

    # Check nested email
    email_facts = [f for f in facts if f.fact_type == FactType.EMAIL]
    assert len(email_facts) == 1
    assert email_facts[0].value == "tech@registrar.example"


def test_normalize_empty_payload(normalizer):
    """Test normalization with minimal data."""
    raw_payload = {}

    facts = normalizer.normalize(raw_payload)

    assert len(facts) == 0


def test_normalize_invalid_type_raises_error(normalizer):
    """Test that non-dict payload raises NormalizationError."""
    with pytest.raises(NormalizationError):
        normalizer.normalize("not a dict")


def test_normalize_invalid_dates(normalizer):
    """Test that invalid dates are skipped gracefully."""
    raw_payload = {
        "ldhName": "example.com",
        "events": [
            {"eventAction": "registration", "eventDate": "invalid-date"},
            {"eventAction": "expiration", "eventDate": "2025-01-15T10:30:00Z"},
        ],
    }

    facts = normalizer.normalize(raw_payload)

    # Only the valid expiration date should be extracted
    event_facts = [
        f
        for f in facts
        if f.fact_type
        in [FactType.DOMAIN_REGISTRATION, FactType.EXPIRATION, FactType.GENERIC]
    ]
    # Should have 1 expiration fact
    assert len([f for f in event_facts if f.fact_type == FactType.EXPIRATION]) == 1
    # Should have 0 registration facts (invalid date)
    assert len([f for f in event_facts if f.fact_type == FactType.DOMAIN_REGISTRATION]) == 0


def test_normalize_last_changed_event(normalizer):
    """Test that last changed events are captured as generic facts."""
    raw_payload = {
        "ldhName": "example.com",
        "events": [
            {
                "eventAction": "last changed",
                "eventDate": "2024-06-15T08:00:00Z",
            },
        ],
    }

    facts = normalizer.normalize(raw_payload)

    generic_facts = [f for f in facts if f.fact_type == FactType.GENERIC]
    assert len(generic_facts) == 1
    assert generic_facts[0].metadata["field"] == "last changed"
