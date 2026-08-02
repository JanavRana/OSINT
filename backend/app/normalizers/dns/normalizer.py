"""
normalizers/dns/normalizer.py

DNS normalizer implementation that converts DNS records to normalized facts.

This normalizer:
    1. Subclasses BaseNormalizer
    2. Registers itself automatically via the @normalizer_registry.register decorator
    3. Handles raw DNS data from the DNS connector
    4. Extracts various DNS record types (A, AAAA, MX, NS, TXT, CNAME, SOA)
    5. Produces NormalizedFact objects for downstream processing
"""

from __future__ import annotations

from typing import Any, ClassVar, List

from ..base import BaseNormalizer
from ..registry import normalizer_registry
from ..types import FactType, NormalizedFact


@normalizer_registry.register
class DnsNormalizer(BaseNormalizer):
    """
    Normalizer for DNS connector output.

    Converts DNS records (A, AAAA, MX, NS, TXT, CNAME, SOA) into
    normalized facts for correlation and analysis.
    """

    connector_name: ClassVar[str] = "dns"

    def normalize(self, raw_payload: dict) -> List[NormalizedFact]:
        """
        Extract normalized facts from DNS records.

        Args:
            raw_payload: Raw DNS data from the DNS connector containing
                        'domain' and 'records' keys

        Returns:
            List of NormalizedFact objects extracted from the DNS data
        """
        facts: List[NormalizedFact] = []

        if not isinstance(raw_payload, dict):
            return facts

        domain = raw_payload.get("domain")
        records = raw_payload.get("records", {})

        if not isinstance(records, dict):
            return facts

        # Extract A records (IPv4 addresses)
        a_records = records.get("A", [])
        for record in a_records:
            if isinstance(record, dict):
                address = record.get("address")
                if address:
                    facts.append(
                        NormalizedFact(
                            fact_type=FactType.DNS_RECORD,
                            value=address,
                            source_connector=self.connector_name,
                            confidence=0.95,
                            metadata={
                                "record_type": "A",
                                "domain": domain,
                                "ip_version": "4",
                            },
                        )
                    )

        # Extract AAAA records (IPv6 addresses)
        aaaa_records = records.get("AAAA", [])
        for record in aaaa_records:
            if isinstance(record, dict):
                address = record.get("address")
                if address:
                    facts.append(
                        NormalizedFact(
                            fact_type=FactType.DNS_RECORD,
                            value=address,
                            source_connector=self.connector_name,
                            confidence=0.95,
                            metadata={
                                "record_type": "AAAA",
                                "domain": domain,
                                "ip_version": "6",
                            },
                        )
                    )

        # Extract MX records (mail servers)
        mx_records = records.get("MX", [])
        for record in mx_records:
            if isinstance(record, dict):
                exchange = record.get("exchange")
                preference = record.get("preference")
                if exchange:
                    facts.append(
                        NormalizedFact(
                            fact_type=FactType.DNS_RECORD,
                            value=exchange,
                            source_connector=self.connector_name,
                            confidence=0.90,
                            metadata={
                                "record_type": "MX",
                                "domain": domain,
                                "preference": preference,
                            },
                        )
                    )

        # Extract NS records (nameservers)
        ns_records = records.get("NS", [])
        for record in ns_records:
            if isinstance(record, dict):
                nameserver = record.get("nameserver")
                if nameserver:
                    facts.append(
                        NormalizedFact(
                            fact_type=FactType.NAMESERVER,
                            value=nameserver,
                            source_connector=self.connector_name,
                            confidence=0.95,
                            metadata={
                                "record_type": "NS",
                                "domain": domain,
                            },
                        )
                    )

        # Extract TXT records (text data)
        txt_records = records.get("TXT", [])
        for record in txt_records:
            if isinstance(record, dict):
                text = record.get("text")
                if text:
                    # Parse TXT records for specific patterns (SPF, DKIM, etc.)
                    fact_metadata: dict[str, Any] = {
                        "record_type": "TXT",
                        "domain": domain,
                    }

                    # Identify special TXT record types
                    if text.startswith("v=spf"):
                        fact_metadata["txt_type"] = "SPF"
                    elif "dkim" in text.lower():
                        fact_metadata["txt_type"] = "DKIM"
                    elif text.startswith("v=DMARC"):
                        fact_metadata["txt_type"] = "DMARC"

                    facts.append(
                        NormalizedFact(
                            fact_type=FactType.DNS_RECORD,
                            value=text,
                            source_connector=self.connector_name,
                            confidence=0.85,
                            metadata=fact_metadata,
                        )
                    )

        # Extract CNAME records (canonical name)
        cname_records = records.get("CNAME", [])
        for record in cname_records:
            if isinstance(record, dict):
                cname = record.get("cname")
                if cname:
                    facts.append(
                        NormalizedFact(
                            fact_type=FactType.DNS_RECORD,
                            value=cname,
                            source_connector=self.connector_name,
                            confidence=0.95,
                            metadata={
                                "record_type": "CNAME",
                                "domain": domain,
                            },
                        )
                    )

        # Extract SOA records (start of authority)
        soa_records = records.get("SOA", [])
        for record in soa_records:
            if isinstance(record, dict):
                mname = record.get("mname")
                if mname:
                    facts.append(
                        NormalizedFact(
                            fact_type=FactType.NAMESERVER,
                            value=mname,
                            source_connector=self.connector_name,
                            confidence=0.90,
                            metadata={
                                "record_type": "SOA",
                                "domain": domain,
                                "role": "primary_nameserver",
                                "rname": record.get("rname"),
                                "serial": record.get("serial"),
                            },
                        )
                    )

        return facts
