"""Tests for SslCertificateNormalizer."""

from datetime import datetime

import pytest

from app.normalizers.ssl_certificate import SslCertificateNormalizer
from app.normalizers.types import FactType


@pytest.fixture
def normalizer():
    return SslCertificateNormalizer()


def test_normalize_full_certificate_data(normalizer):
    """Test normalization of a complete SSL certificate."""
    raw_payload = {
        "domain": "example.com",
        "port": 443,
        "certificate": {
            "subject": {
                "commonname": "example.com",
                "organizationname": "Example Organization",
                "countryname": "US",
            },
            "issuer": {
                "commonname": "DigiCert Global Root CA",
                "organizationname": "DigiCert Inc",
            },
            "not_before": "2024-01-01T00:00:00",
            "not_after": "2025-01-01T00:00:00",
            "serial_number": "0A1B2C3D4E5F6789",
            "subject_alt_names": [
                {"type": "DNS", "value": "example.com"},
                {"type": "DNS", "value": "www.example.com"},
                {"type": "DNS", "value": "*.example.com"},
            ],
        },
    }

    facts = normalizer.normalize(raw_payload)

    assert len(facts) > 0

    # Check certificate common name
    cn_facts = [
        f
        for f in facts
        if f.fact_type == FactType.CERTIFICATE
        and f.metadata.get("field") == "common_name"
    ]
    assert len(cn_facts) == 1
    assert cn_facts[0].value == "example.com"

    # Check organization
    org_facts = [
        f
        for f in facts
        if f.fact_type == FactType.ORGANIZATION
        and f.metadata.get("field") == "certificate_organization"
    ]
    assert len(org_facts) == 1
    assert org_facts[0].value == "Example Organization"

    # Check country
    country_facts = [
        f
        for f in facts
        if f.fact_type == FactType.LOCATION
        and f.metadata.get("field") == "certificate_country"
    ]
    assert len(country_facts) == 1
    assert country_facts[0].value == "US"

    # Check issuer
    issuer_facts = [
        f
        for f in facts
        if f.fact_type == FactType.ORGANIZATION
        and f.metadata.get("field") == "certificate_issuer"
    ]
    assert len(issuer_facts) == 1
    assert issuer_facts[0].value == "DigiCert Inc"
    assert issuer_facts[0].metadata["role"] == "certificate_authority"

    # Check validity dates
    issued_facts = [
        f
        for f in facts
        if f.fact_type == FactType.CERTIFICATE
        and f.metadata.get("field") == "certificate_issued"
    ]
    assert len(issued_facts) == 1
    assert issued_facts[0].occurred_at.year == 2024

    expiration_facts = [
        f
        for f in facts
        if f.fact_type == FactType.EXPIRATION
        and f.metadata.get("field") == "certificate_expiration"
    ]
    assert len(expiration_facts) == 1
    assert expiration_facts[0].occurred_at.year == 2025

    # Check SANs
    san_facts = [
        f
        for f in facts
        if f.fact_type == FactType.DOMAIN and f.metadata.get("field") == "certificate_san"
    ]
    assert len(san_facts) == 3
    san_values = {f.value for f in san_facts}
    assert "example.com" in san_values
    assert "www.example.com" in san_values
    assert "*.example.com" in san_values

    # Check serial number
    serial_facts = [
        f
        for f in facts
        if f.fact_type == FactType.CERTIFICATE
        and f.metadata.get("field") == "serial_number"
    ]
    assert len(serial_facts) == 1
    assert serial_facts[0].value == "0A1B2C3D4E5F6789"


def test_normalize_subject_with_lowercase_keys(normalizer):
    """Test normalization with lowercase subject keys (cn, o, c)."""
    raw_payload = {
        "domain": "example.com",
        "certificate": {
            "subject": {
                "cn": "example.com",
                "o": "Example Org",
                "c": "GB",
            },
        },
    }

    facts = normalizer.normalize(raw_payload)

    # Check common name
    cn_facts = [
        f
        for f in facts
        if f.fact_type == FactType.CERTIFICATE
        and f.metadata.get("field") == "common_name"
    ]
    assert len(cn_facts) == 1
    assert cn_facts[0].value == "example.com"

    # Check organization
    org_facts = [
        f
        for f in facts
        if f.fact_type == FactType.ORGANIZATION
        and f.metadata.get("field") == "certificate_organization"
    ]
    assert len(org_facts) == 1
    assert org_facts[0].value == "Example Org"

    # Check country
    country_facts = [
        f
        for f in facts
        if f.fact_type == FactType.LOCATION
        and f.metadata.get("field") == "certificate_country"
    ]
    assert len(country_facts) == 1
    assert country_facts[0].value == "GB"


def test_normalize_issuer_common_name_fallback(normalizer):
    """Test that issuer CN is used when organization is not present."""
    raw_payload = {
        "domain": "example.com",
        "certificate": {
            "issuer": {
                "commonname": "Let's Encrypt Authority X3",
            },
        },
    }

    facts = normalizer.normalize(raw_payload)

    issuer_facts = [
        f
        for f in facts
        if f.fact_type == FactType.ORGANIZATION
        and f.metadata.get("field") == "certificate_issuer"
    ]
    assert len(issuer_facts) == 1
    assert issuer_facts[0].value == "Let's Encrypt Authority X3"


def test_normalize_san_with_ip_address(normalizer):
    """Test normalization of SANs with IP addresses."""
    raw_payload = {
        "domain": "example.com",
        "certificate": {
            "subject_alt_names": [
                {"type": "DNS", "value": "example.com"},
                {"type": "IP Address", "value": "93.184.216.34"},
            ],
        },
    }

    facts = normalizer.normalize(raw_payload)

    # Check DNS SAN
    dns_san_facts = [
        f
        for f in facts
        if f.fact_type == FactType.DOMAIN and f.metadata.get("san_type") == "DNS"
    ]
    assert len(dns_san_facts) == 1
    assert dns_san_facts[0].value == "example.com"

    # Check IP Address SAN
    ip_san_facts = [
        f
        for f in facts
        if f.fact_type == FactType.DNS_RECORD
        and f.metadata.get("san_type") == "IP Address"
    ]
    assert len(ip_san_facts) == 1
    assert ip_san_facts[0].value == "93.184.216.34"


def test_normalize_san_lowercase_conversion(normalizer):
    """Test that DNS SANs are converted to lowercase."""
    raw_payload = {
        "domain": "example.com",
        "certificate": {
            "subject_alt_names": [
                {"type": "DNS", "value": "EXAMPLE.COM"},
                {"type": "DNS", "value": "WWW.EXAMPLE.COM"},
            ],
        },
    }

    facts = normalizer.normalize(raw_payload)

    san_facts = [
        f for f in facts if f.fact_type == FactType.DOMAIN
    ]
    assert len(san_facts) == 2
    san_values = {f.value for f in san_facts}
    assert "example.com" in san_values
    assert "www.example.com" in san_values


def test_normalize_minimal_certificate(normalizer):
    """Test normalization with minimal certificate data."""
    raw_payload = {
        "domain": "example.com",
        "certificate": {
            "subject": {
                "commonname": "example.com",
            },
        },
    }

    facts = normalizer.normalize(raw_payload)

    # Should only extract the common name
    assert len(facts) == 1
    assert facts[0].fact_type == FactType.CERTIFICATE
    assert facts[0].value == "example.com"


def test_normalize_empty_certificate(normalizer):
    """Test normalization with empty certificate data."""
    raw_payload = {
        "domain": "example.com",
        "certificate": {},
    }

    facts = normalizer.normalize(raw_payload)

    assert len(facts) == 0


def test_normalize_no_certificate(normalizer):
    """Test normalization with missing certificate key."""
    raw_payload = {
        "domain": "example.com",
        "port": 443,
    }

    facts = normalizer.normalize(raw_payload)

    assert len(facts) == 0


def test_normalize_invalid_payload_type(normalizer):
    """Test normalization with invalid payload type."""
    raw_payload = "not a dict"

    facts = normalizer.normalize(raw_payload)

    assert len(facts) == 0


def test_normalize_certificate_not_dict(normalizer):
    """Test normalization when certificate is not a dict."""
    raw_payload = {
        "domain": "example.com",
        "certificate": "not a dict",
    }

    facts = normalizer.normalize(raw_payload)

    assert len(facts) == 0


def test_normalize_invalid_date_strings(normalizer):
    """Test that invalid date strings are skipped gracefully."""
    raw_payload = {
        "domain": "example.com",
        "certificate": {
            "not_before": "invalid-date",
            "not_after": "2025-01-01T00:00:00",
        },
    }

    facts = normalizer.normalize(raw_payload)

    # Only the valid expiration date should be extracted
    issued_facts = [
        f
        for f in facts
        if f.fact_type == FactType.CERTIFICATE
        and f.metadata.get("field") == "certificate_issued"
    ]
    assert len(issued_facts) == 0  # Invalid date skipped

    expiration_facts = [
        f
        for f in facts
        if f.fact_type == FactType.EXPIRATION
        and f.metadata.get("field") == "certificate_expiration"
    ]
    assert len(expiration_facts) == 1


def test_normalize_date_with_timezone(normalizer):
    """Test normalization of dates with timezone."""
    raw_payload = {
        "domain": "example.com",
        "certificate": {
            "not_before": "2024-01-01T00:00:00Z",
            "not_after": "2025-01-01T00:00:00+00:00",
        },
    }

    facts = normalizer.normalize(raw_payload)

    issued_facts = [
        f
        for f in facts
        if f.fact_type == FactType.CERTIFICATE
        and f.metadata.get("field") == "certificate_issued"
    ]
    assert len(issued_facts) == 1
    assert issued_facts[0].occurred_at.year == 2024

    expiration_facts = [
        f
        for f in facts
        if f.fact_type == FactType.EXPIRATION
        and f.metadata.get("field") == "certificate_expiration"
    ]
    assert len(expiration_facts) == 1
    assert expiration_facts[0].occurred_at.year == 2025


def test_normalize_confidence_scores(normalizer):
    """Test that confidence scores are appropriate for different fact types."""
    raw_payload = {
        "domain": "example.com",
        "certificate": {
            "subject": {
                "commonname": "example.com",
                "organizationname": "Example Org",
            },
            "issuer": {
                "organizationname": "CA Org",
            },
            "serial_number": "ABC123",
            "subject_alt_names": [
                {"type": "DNS", "value": "www.example.com"},
                {"type": "IP Address", "value": "93.184.216.34"},
            ],
        },
    }

    facts = normalizer.normalize(raw_payload)

    # Certificate common name and serial should have highest confidence
    cn_facts = [
        f
        for f in facts
        if f.fact_type == FactType.CERTIFICATE
        and f.metadata.get("field") == "common_name"
    ]
    assert cn_facts[0].confidence == 0.95

    serial_facts = [
        f
        for f in facts
        if f.fact_type == FactType.CERTIFICATE
        and f.metadata.get("field") == "serial_number"
    ]
    assert serial_facts[0].confidence == 1.0

    # Issuer should have high confidence
    issuer_facts = [
        f
        for f in facts
        if f.metadata.get("field") == "certificate_issuer"
    ]
    assert issuer_facts[0].confidence == 0.90

    # Subject organization should have good confidence
    org_facts = [
        f
        for f in facts
        if f.metadata.get("field") == "certificate_organization"
    ]
    assert org_facts[0].confidence == 0.85

    # DNS SANs should have high confidence
    dns_san_facts = [
        f
        for f in facts
        if f.fact_type == FactType.DOMAIN and f.metadata.get("san_type") == "DNS"
    ]
    assert dns_san_facts[0].confidence == 0.90

    # IP SANs should have good confidence
    ip_san_facts = [
        f
        for f in facts
        if f.fact_type == FactType.DNS_RECORD
        and f.metadata.get("san_type") == "IP Address"
    ]
    assert ip_san_facts[0].confidence == 0.85


def test_normalize_metadata_includes_domain(normalizer):
    """Test that domain is included in metadata for all facts."""
    raw_payload = {
        "domain": "example.com",
        "certificate": {
            "subject": {
                "commonname": "example.com",
                "organizationname": "Example Org",
            },
            "serial_number": "ABC123",
        },
    }

    facts = normalizer.normalize(raw_payload)

    # All facts should have domain in metadata
    for fact in facts:
        assert "domain" in fact.metadata
        assert fact.metadata["domain"] == "example.com"


def test_normalize_wildcard_certificate(normalizer):
    """Test normalization of wildcard certificates."""
    raw_payload = {
        "domain": "example.com",
        "certificate": {
            "subject": {
                "commonname": "*.example.com",
            },
            "subject_alt_names": [
                {"type": "DNS", "value": "*.example.com"},
                {"type": "DNS", "value": "example.com"},
            ],
        },
    }

    facts = normalizer.normalize(raw_payload)

    # Check wildcard common name
    cn_facts = [
        f
        for f in facts
        if f.fact_type == FactType.CERTIFICATE
        and f.metadata.get("field") == "common_name"
    ]
    assert len(cn_facts) == 1
    assert cn_facts[0].value == "*.example.com"

    # Check wildcard in SANs
    san_facts = [f for f in facts if f.fact_type == FactType.DOMAIN]
    san_values = {f.value for f in san_facts}
    assert "*.example.com" in san_values
    assert "example.com" in san_values
