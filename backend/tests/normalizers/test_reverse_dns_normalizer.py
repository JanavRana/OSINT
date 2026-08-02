"""Tests for ReverseDnsNormalizer."""

import pytest

from app.normalizers.reverse_dns import ReverseDnsNormalizer
from app.normalizers.types import FactType


@pytest.fixture
def normalizer():
    return ReverseDnsNormalizer()


def test_normalize_full_reverse_dns_data(normalizer):
    """Test normalization of a complete reverse DNS response."""
    raw_payload = {
        "ip_address": "8.8.8.8",
        "hostnames": [
            "dns.google",
            "google-public-dns-a.google.com",
        ],
    }

    facts = normalizer.normalize(raw_payload)

    assert len(facts) == 2

    # Check that all facts are domain facts
    for fact in facts:
        assert fact.fact_type == FactType.DOMAIN
        assert fact.source_connector == "reverse_dns"
        assert fact.confidence == 0.90

    # Check hostnames
    hostname_values = {f.value for f in facts}
    assert "dns.google" in hostname_values
    assert "google-public-dns-a.google.com" in hostname_values

    # Check metadata
    for fact in facts:
        assert fact.metadata["record_type"] == "PTR"
        assert fact.metadata["ip_address"] == "8.8.8.8"
        assert fact.metadata["reverse_dns"] is True


def test_normalize_single_hostname(normalizer):
    """Test normalization with a single hostname."""
    raw_payload = {
        "ip_address": "1.1.1.1",
        "hostnames": ["one.one.one.one"],
    }

    facts = normalizer.normalize(raw_payload)

    assert len(facts) == 1
    assert facts[0].fact_type == FactType.DOMAIN
    assert facts[0].value == "one.one.one.one"
    assert facts[0].metadata["ip_address"] == "1.1.1.1"


def test_normalize_ipv6_address(normalizer):
    """Test normalization with an IPv6 address."""
    raw_payload = {
        "ip_address": "2001:4860:4860::8888",
        "hostnames": ["dns.google"],
    }

    facts = normalizer.normalize(raw_payload)

    assert len(facts) == 1
    assert facts[0].fact_type == FactType.DOMAIN
    assert facts[0].value == "dns.google"
    assert facts[0].metadata["ip_address"] == "2001:4860:4860::8888"


def test_normalize_empty_hostnames(normalizer):
    """Test normalization with no hostnames found."""
    raw_payload = {
        "ip_address": "192.168.1.1",
        "hostnames": [],
    }

    facts = normalizer.normalize(raw_payload)

    assert len(facts) == 0


def test_normalize_hostnames_with_whitespace(normalizer):
    """Test that hostnames are trimmed."""
    raw_payload = {
        "ip_address": "8.8.8.8",
        "hostnames": [
            "  dns.google  ",
            "  google-public-dns.google.com  ",
        ],
    }

    facts = normalizer.normalize(raw_payload)

    assert len(facts) == 2
    hostname_values = {f.value for f in facts}
    assert "dns.google" in hostname_values
    assert "google-public-dns.google.com" in hostname_values


def test_normalize_lowercase_conversion(normalizer):
    """Test that hostnames are converted to lowercase."""
    raw_payload = {
        "ip_address": "8.8.8.8",
        "hostnames": [
            "DNS.GOOGLE",
            "Google-Public-DNS.Google.Com",
        ],
    }

    facts = normalizer.normalize(raw_payload)

    assert len(facts) == 2
    hostname_values = {f.value for f in facts}
    assert "dns.google" in hostname_values
    assert "google-public-dns.google.com" in hostname_values


def test_normalize_empty_string_hostname(normalizer):
    """Test that empty string hostnames are skipped."""
    raw_payload = {
        "ip_address": "8.8.8.8",
        "hostnames": [
            "dns.google",
            "",
            "   ",
            "google-public-dns.google.com",
        ],
    }

    facts = normalizer.normalize(raw_payload)

    # Should only extract the 2 valid hostnames
    assert len(facts) == 2
    hostname_values = {f.value for f in facts}
    assert "dns.google" in hostname_values
    assert "google-public-dns.google.com" in hostname_values


def test_normalize_invalid_payload_type(normalizer):
    """Test normalization with invalid payload type."""
    raw_payload = "not a dict"

    facts = normalizer.normalize(raw_payload)

    assert len(facts) == 0


def test_normalize_missing_hostnames_key(normalizer):
    """Test normalization with missing hostnames key."""
    raw_payload = {
        "ip_address": "8.8.8.8",
    }

    facts = normalizer.normalize(raw_payload)

    assert len(facts) == 0


def test_normalize_hostnames_not_list(normalizer):
    """Test normalization when hostnames is not a list."""
    raw_payload = {
        "ip_address": "8.8.8.8",
        "hostnames": "not a list",
    }

    facts = normalizer.normalize(raw_payload)

    assert len(facts) == 0


def test_normalize_hostname_non_string(normalizer):
    """Test that non-string hostnames are skipped."""
    raw_payload = {
        "ip_address": "8.8.8.8",
        "hostnames": [
            "dns.google",
            123,  # Non-string
            None,  # None value
            {"hostname": "invalid"},  # Dict
            "google-public-dns.google.com",
        ],
    }

    facts = normalizer.normalize(raw_payload)

    # Should only extract the 2 valid string hostnames
    assert len(facts) == 2
    hostname_values = {f.value for f in facts}
    assert "dns.google" in hostname_values
    assert "google-public-dns.google.com" in hostname_values


def test_normalize_missing_ip_address(normalizer):
    """Test normalization with missing ip_address key."""
    raw_payload = {
        "hostnames": ["dns.google"],
    }

    facts = normalizer.normalize(raw_payload)

    # Should still extract the hostname, ip_address is just metadata
    assert len(facts) == 1
    assert facts[0].value == "dns.google"
    assert facts[0].metadata["ip_address"] is None


def test_normalize_with_error_field(normalizer):
    """Test normalization when response contains an error."""
    raw_payload = {
        "ip_address": "192.0.2.1",
        "hostnames": [],
        "error": "No reverse DNS record found for 192.0.2.1 (NXDOMAIN)",
    }

    facts = normalizer.normalize(raw_payload)

    # Should return empty list when no hostnames found
    assert len(facts) == 0


def test_normalize_confidence_score(normalizer):
    """Test that confidence score is appropriate for reverse DNS."""
    raw_payload = {
        "ip_address": "8.8.8.8",
        "hostnames": ["dns.google"],
    }

    facts = normalizer.normalize(raw_payload)

    assert len(facts) == 1
    # Reverse DNS should have slightly lower confidence than forward DNS
    assert facts[0].confidence == 0.90


def test_normalize_metadata_structure(normalizer):
    """Test that metadata contains all expected fields."""
    raw_payload = {
        "ip_address": "8.8.8.8",
        "hostnames": ["dns.google"],
    }

    facts = normalizer.normalize(raw_payload)

    assert len(facts) == 1
    metadata = facts[0].metadata

    assert "record_type" in metadata
    assert metadata["record_type"] == "PTR"
    assert "ip_address" in metadata
    assert metadata["ip_address"] == "8.8.8.8"
    assert "reverse_dns" in metadata
    assert metadata["reverse_dns"] is True


def test_normalize_multiple_ips_same_hostname(normalizer):
    """Test that the same hostname from different IPs is handled correctly."""
    # This would typically be separate connector calls, but testing the
    # normalization logic independently
    raw_payload_1 = {
        "ip_address": "8.8.8.8",
        "hostnames": ["dns.google"],
    }
    raw_payload_2 = {
        "ip_address": "8.8.4.4",
        "hostnames": ["dns.google"],
    }

    facts_1 = normalizer.normalize(raw_payload_1)
    facts_2 = normalizer.normalize(raw_payload_2)

    # Each should produce one fact
    assert len(facts_1) == 1
    assert len(facts_2) == 1

    # Same hostname value
    assert facts_1[0].value == facts_2[0].value == "dns.google"

    # Different IP addresses in metadata
    assert facts_1[0].metadata["ip_address"] == "8.8.8.8"
    assert facts_2[0].metadata["ip_address"] == "8.8.4.4"
