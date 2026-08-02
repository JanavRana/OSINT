"""Tests for DnsNormalizer."""

import pytest

from app.normalizers.dns import DnsNormalizer
from app.normalizers.types import FactType


@pytest.fixture
def normalizer():
    return DnsNormalizer()


def test_normalize_full_dns_data(normalizer):
    """Test normalization of a complete DNS response."""
    raw_payload = {
        "domain": "example.com",
        "records": {
            "A": [
                {"address": "93.184.216.34"},
                {"address": "93.184.216.35"},
            ],
            "AAAA": [
                {"address": "2606:2800:220:1:248:1893:25c8:1946"},
            ],
            "MX": [
                {"preference": 10, "exchange": "mail.example.com"},
                {"preference": 20, "exchange": "mail2.example.com"},
            ],
            "NS": [
                {"nameserver": "ns1.example.com"},
                {"nameserver": "ns2.example.com"},
            ],
            "TXT": [
                {"text": "v=spf1 include:_spf.example.com ~all"},
                {"text": "v=DMARC1; p=none; rua=mailto:dmarc@example.com"},
            ],
            "CNAME": [
                {"cname": "www.example.com"},
            ],
            "SOA": [
                {
                    "mname": "ns1.example.com",
                    "rname": "admin.example.com",
                    "serial": 2024010101,
                    "refresh": 3600,
                    "retry": 600,
                    "expire": 86400,
                    "minimum": 300,
                },
            ],
        },
    }

    facts = normalizer.normalize(raw_payload)

    assert len(facts) > 0

    # Check A records
    a_facts = [
        f
        for f in facts
        if f.fact_type == FactType.DNS_RECORD
        and f.metadata.get("record_type") == "A"
    ]
    assert len(a_facts) == 2
    a_values = {f.value for f in a_facts}
    assert "93.184.216.34" in a_values
    assert "93.184.216.35" in a_values

    # Check AAAA records
    aaaa_facts = [
        f
        for f in facts
        if f.fact_type == FactType.DNS_RECORD
        and f.metadata.get("record_type") == "AAAA"
    ]
    assert len(aaaa_facts) == 1
    assert aaaa_facts[0].value == "2606:2800:220:1:248:1893:25c8:1946"
    assert aaaa_facts[0].metadata["ip_version"] == "6"

    # Check MX records
    mx_facts = [
        f
        for f in facts
        if f.fact_type == FactType.DNS_RECORD
        and f.metadata.get("record_type") == "MX"
    ]
    assert len(mx_facts) == 2
    mx_values = {f.value for f in mx_facts}
    assert "mail.example.com" in mx_values
    assert "mail2.example.com" in mx_values

    # Check NS records
    ns_facts = [
        f for f in facts if f.fact_type == FactType.NAMESERVER
        and f.metadata.get("record_type") == "NS"
    ]
    assert len(ns_facts) == 2
    ns_values = {f.value for f in ns_facts}
    assert "ns1.example.com" in ns_values
    assert "ns2.example.com" in ns_values

    # Check TXT records
    txt_facts = [
        f
        for f in facts
        if f.fact_type == FactType.DNS_RECORD
        and f.metadata.get("record_type") == "TXT"
    ]
    assert len(txt_facts) == 2

    # Check SPF record is identified
    spf_facts = [f for f in txt_facts if f.metadata.get("txt_type") == "SPF"]
    assert len(spf_facts) == 1

    # Check DMARC record is identified
    dmarc_facts = [f for f in txt_facts if f.metadata.get("txt_type") == "DMARC"]
    assert len(dmarc_facts) == 1

    # Check CNAME records
    cname_facts = [
        f
        for f in facts
        if f.fact_type == FactType.DNS_RECORD
        and f.metadata.get("record_type") == "CNAME"
    ]
    assert len(cname_facts) == 1
    assert cname_facts[0].value == "www.example.com"

    # Check SOA records
    soa_facts = [
        f for f in facts if f.metadata.get("record_type") == "SOA"
    ]
    assert len(soa_facts) == 1
    assert soa_facts[0].value == "ns1.example.com"
    assert soa_facts[0].metadata["role"] == "primary_nameserver"


def test_normalize_a_records_only(normalizer):
    """Test normalization with only A records."""
    raw_payload = {
        "domain": "example.com",
        "records": {
            "A": [
                {"address": "93.184.216.34"},
            ],
        },
    }

    facts = normalizer.normalize(raw_payload)

    assert len(facts) == 1
    assert facts[0].fact_type == FactType.DNS_RECORD
    assert facts[0].value == "93.184.216.34"
    assert facts[0].metadata["record_type"] == "A"
    assert facts[0].metadata["ip_version"] == "4"


def test_normalize_mx_with_preference(normalizer):
    """Test that MX record preference is stored in metadata."""
    raw_payload = {
        "domain": "example.com",
        "records": {
            "MX": [
                {"preference": 10, "exchange": "mail1.example.com"},
                {"preference": 20, "exchange": "mail2.example.com"},
            ],
        },
    }

    facts = normalizer.normalize(raw_payload)

    assert len(facts) == 2
    for fact in facts:
        assert fact.fact_type == FactType.DNS_RECORD
        assert fact.metadata["record_type"] == "MX"
        assert "preference" in fact.metadata


def test_normalize_txt_spf_detection(normalizer):
    """Test that SPF records are properly identified."""
    raw_payload = {
        "domain": "example.com",
        "records": {
            "TXT": [
                {"text": "v=spf1 include:_spf.google.com ~all"},
            ],
        },
    }

    facts = normalizer.normalize(raw_payload)

    assert len(facts) == 1
    assert facts[0].fact_type == FactType.DNS_RECORD
    assert facts[0].metadata["txt_type"] == "SPF"
    assert "v=spf1" in facts[0].value


def test_normalize_txt_dkim_detection(normalizer):
    """Test that DKIM records are properly identified."""
    raw_payload = {
        "domain": "example.com",
        "records": {
            "TXT": [
                {"text": "v=DKIM1; k=rsa; p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQ..."},
            ],
        },
    }

    facts = normalizer.normalize(raw_payload)

    assert len(facts) == 1
    assert facts[0].fact_type == FactType.DNS_RECORD
    assert facts[0].metadata["txt_type"] == "DKIM"


def test_normalize_soa_metadata(normalizer):
    """Test that SOA record metadata is properly extracted."""
    raw_payload = {
        "domain": "example.com",
        "records": {
            "SOA": [
                {
                    "mname": "ns1.example.com",
                    "rname": "hostmaster.example.com",
                    "serial": 2024010101,
                    "refresh": 7200,
                    "retry": 1800,
                    "expire": 604800,
                    "minimum": 86400,
                },
            ],
        },
    }

    facts = normalizer.normalize(raw_payload)

    assert len(facts) == 1
    soa_fact = facts[0]
    assert soa_fact.fact_type == FactType.NAMESERVER
    assert soa_fact.value == "ns1.example.com"
    assert soa_fact.metadata["record_type"] == "SOA"
    assert soa_fact.metadata["rname"] == "hostmaster.example.com"
    assert soa_fact.metadata["serial"] == 2024010101


def test_normalize_empty_records(normalizer):
    """Test normalization with no DNS records."""
    raw_payload = {
        "domain": "example.com",
        "records": {},
    }

    facts = normalizer.normalize(raw_payload)

    assert len(facts) == 0


def test_normalize_invalid_payload(normalizer):
    """Test normalization with invalid payload structure."""
    raw_payload = "not a dict"

    facts = normalizer.normalize(raw_payload)

    assert len(facts) == 0


def test_normalize_missing_domain(normalizer):
    """Test normalization with missing domain field."""
    raw_payload = {
        "records": {
            "A": [{"address": "93.184.216.34"}],
        },
    }

    facts = normalizer.normalize(raw_payload)

    # Should still extract facts, domain is just metadata
    assert len(facts) == 1
    assert facts[0].metadata["domain"] is None


def test_normalize_empty_record_lists(normalizer):
    """Test normalization with empty record type lists."""
    raw_payload = {
        "domain": "example.com",
        "records": {
            "A": [],
            "MX": [],
            "NS": [],
        },
    }

    facts = normalizer.normalize(raw_payload)

    assert len(facts) == 0


def test_normalize_malformed_record(normalizer):
    """Test that malformed records are skipped gracefully."""
    raw_payload = {
        "domain": "example.com",
        "records": {
            "A": [
                {"address": "93.184.216.34"},
                {"wrong_key": "invalid"},  # Malformed record
                {"address": "93.184.216.35"},
            ],
        },
    }

    facts = normalizer.normalize(raw_payload)

    # Should extract the 2 valid A records
    a_facts = [
        f
        for f in facts
        if f.fact_type == FactType.DNS_RECORD
        and f.metadata.get("record_type") == "A"
    ]
    assert len(a_facts) == 2


def test_normalize_confidence_scores(normalizer):
    """Test that confidence scores are appropriate for different record types."""
    raw_payload = {
        "domain": "example.com",
        "records": {
            "A": [{"address": "93.184.216.34"}],
            "NS": [{"nameserver": "ns1.example.com"}],
            "TXT": [{"text": "v=spf1 ~all"}],
        },
    }

    facts = normalizer.normalize(raw_payload)

    # A records should have high confidence
    a_facts = [
        f
        for f in facts
        if f.fact_type == FactType.DNS_RECORD
        and f.metadata.get("record_type") == "A"
    ]
    assert a_facts[0].confidence == 0.95

    # NS records should have high confidence
    ns_facts = [f for f in facts if f.fact_type == FactType.NAMESERVER]
    assert ns_facts[0].confidence == 0.95

    # TXT records should have slightly lower confidence
    txt_facts = [
        f
        for f in facts
        if f.fact_type == FactType.DNS_RECORD
        and f.metadata.get("record_type") == "TXT"
    ]
    assert txt_facts[0].confidence == 0.85
