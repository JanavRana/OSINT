"""
normalizers/virustotal/normalizer.py

VirusTotal Normalizer.

Transforms raw VirusTotal v3 payload into normalized facts, extracting:
- Multi-engine malicious/suspicious threat indicators
- VirusTotal community reputation score
- Threat tags and vendor classifications
- Hosting ISP / AS Owner & Geolocation country (for IPs)
- Passive DNS records (for Domains)
"""

from __future__ import annotations

import logging
from typing import Any, ClassVar, Dict, List

from ..base import BaseNormalizer
from ..registry import normalizer_registry
from ..types import FactType, NormalizationError, NormalizedFact

logger = logging.getLogger("osint-aggregator")


@normalizer_registry.register
class VirusTotalNormalizer(BaseNormalizer):
    """
    Normalizer for VirusTotal v3 raw payload.
    """

    connector_name: ClassVar[str] = "virustotal"

    def normalize(self, raw_data: Any) -> List[NormalizedFact]:
        """
        Transform raw VirusTotal dict payload into normalized facts.
        """
        if not isinstance(raw_data, dict):
            raise NormalizationError(
                f"VirusTotalNormalizer expected dict, got {type(raw_data).__name__}"
            )

        facts: List[NormalizedFact] = []

        if not raw_data.get("vt_matched"):
            return facts

        # 1. Multi-Engine Security Analysis Stats
        stats = raw_data.get("last_analysis_stats") or {}
        if isinstance(stats, dict) and stats:
            malicious = int(stats.get("malicious", 0))
            suspicious = int(stats.get("suspicious", 0))
            harmless = int(stats.get("harmless", 0))
            undetected = int(stats.get("undetected", 0))

            if malicious > 0 or suspicious > 0:
                risk_level = "CRITICAL" if malicious >= 5 else ("HIGH" if malicious > 0 else "MEDIUM")
                facts.append(
                    NormalizedFact(
                        source_connector=self.connector_name,
                        fact_type=FactType.GENERIC,
                        value=f"VIRUSTOTAL THREAT FLAG: {malicious} Malicious / {suspicious} Suspicious Engines",
                        confidence=0.95,
                        metadata={
                            "field": "vt_threat_flag",
                            "malicious": malicious,
                            "suspicious": suspicious,
                            "harmless": harmless,
                            "undetected": undetected,
                            "risk_level": risk_level,
                            "data_label": "VirusTotal Threat Rating",
                            "note": f"Target flagged by {malicious} malicious security vendor engines on VirusTotal.",
                        },
                    )
                )
            else:
                facts.append(
                    NormalizedFact(
                        source_connector=self.connector_name,
                        fact_type=FactType.GENERIC,
                        value=f"VIRUSTOTAL CLEAN: 0 Malicious Flags ({harmless} engines clean)",
                        confidence=0.90,
                        metadata={
                            "field": "vt_threat_flag",
                            "malicious": 0,
                            "harmless": harmless,
                            "risk_level": "LOW",
                            "data_label": "VirusTotal Threat Rating",
                        },
                    )
                )

        # 2. Community Reputation Score
        reputation = raw_data.get("reputation")
        if reputation is not None and isinstance(reputation, (int, float)):
            facts.append(
                NormalizedFact(
                    source_connector=self.connector_name,
                    fact_type=FactType.GENERIC,
                    value=f"VIRUSTOTAL REPUTATION SCORE: {reputation}",
                    confidence=0.85,
                    metadata={
                        "field": "vt_reputation",
                        "reputation_score": reputation,
                        "data_label": "Community Reputation",
                    },
                )
            )

        # 3. Threat Tags
        tags = raw_data.get("tags")
        if isinstance(tags, list) and tags:
            tag_list = [str(t).strip() for t in tags if t]
            if tag_list:
                facts.append(
                    NormalizedFact(
                        source_connector=self.connector_name,
                        fact_type=FactType.GENERIC,
                        value=f"VIRUSTOTAL TAGS: {', '.join(tag_list)}",
                        confidence=0.85,
                        metadata={
                            "field": "vt_tags",
                            "tags": tag_list,
                            "data_label": "VirusTotal Threat Tags",
                        },
                    )
                )

        # 4. Security Categories
        categories = raw_data.get("categories")
        if isinstance(categories, dict) and categories:
            cat_vals = list({str(v).strip() for v in categories.values() if v})
            if cat_vals:
                facts.append(
                    NormalizedFact(
                        source_connector=self.connector_name,
                        fact_type=FactType.GENERIC,
                        value=f"VIRUSTOTAL CATEGORIES: {', '.join(cat_vals[:5])}",
                        confidence=0.80,
                        metadata={
                            "field": "vt_categories",
                            "categories": cat_vals,
                            "data_label": "Vendor Categories",
                        },
                    )
                )

        # 5. AS Owner & ASN (for IP)
        as_owner = raw_data.get("as_owner")
        asn = raw_data.get("asn")
        if as_owner or asn:
            owner_str = f"AS{asn} {as_owner}".strip() if (asn and as_owner) else (f"AS{asn}" if asn else str(as_owner))
            facts.append(
                NormalizedFact(
                    source_connector=self.connector_name,
                    fact_type=FactType.ORGANIZATION,
                    value=owner_str,
                    confidence=0.85,
                    metadata={
                        "field": "vt_as_owner",
                        "as_owner": as_owner,
                        "asn": asn,
                    },
                )
            )

        # 6. Geolocation Country (for IP)
        country = raw_data.get("country")
        if country and isinstance(country, str) and country.strip():
            facts.append(
                NormalizedFact(
                    source_connector=self.connector_name,
                    fact_type=FactType.LOCATION,
                    value=country.strip(),
                    confidence=0.80,
                    metadata={
                        "field": "vt_country",
                        "country_code": country.strip(),
                    },
                )
            )

        # 7. Discovered Passive DNS Records (Only A and MX records - Filter out TXT/SOA/AAAA site verification noise)
        dns_records = raw_data.get("last_dns_records")
        if isinstance(dns_records, list):
            for rec in dns_records:
                if isinstance(rec, dict):
                    rec_type = str(rec.get("type", "")).upper()
                    rec_val = str(rec.get("value", "")).strip()

                    # Only extract high-value target IPs (A records) and Mail Servers (MX records)
                    if rec_type in ("A", "MX") and rec_val:
                        # Clean display value: strip preference prefix from MX if present
                        clean_val = rec_val.split()[-1] if rec_type == "MX" else rec_val
                        facts.append(
                            NormalizedFact(
                                source_connector=self.connector_name,
                                fact_type=FactType.DNS_RECORD if rec_type == "MX" else FactType.GENERIC,
                                value=clean_val,
                                confidence=0.85,
                                metadata={
                                    "field": "vt_dns_record",
                                    "record_type": rec_type,
                                    "value": clean_val,
                                    "ttl": rec.get("ttl"),
                                    "source": "VirusTotal Passive DNS",
                                },
                            )
                        )

        return facts

