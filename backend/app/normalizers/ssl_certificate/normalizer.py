"""
normalizers/ssl_certificate/normalizer.py

SSL Certificate normalizer implementation that converts certificate data to normalized facts.

This normalizer:
    1. Subclasses BaseNormalizer
    2. Registers itself automatically via the @normalizer_registry.register decorator
    3. Handles raw SSL certificate data from the SSL Certificate connector
    4. Extracts subject, issuer, validity dates, SANs, and organization info
    5. Produces NormalizedFact objects for downstream processing
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, ClassVar, List, Optional

from ..base import BaseNormalizer
from ..registry import normalizer_registry
from ..types import FactType, NormalizedFact


@normalizer_registry.register
class SslCertificateNormalizer(BaseNormalizer):
    """
    Normalizer for SSL Certificate connector output.

    Converts SSL/TLS certificate data into normalized facts,
    extracting information about certificate holders, issuers,
    validity periods, and alternative names.
    """

    connector_name: ClassVar[str] = "ssl_certificate"

    def normalize(self, raw_payload: dict) -> List[NormalizedFact]:
        """
        Extract normalized facts from SSL certificate data.

        Args:
            raw_payload: Raw SSL certificate data from the SSL Certificate connector
                        containing 'domain', 'port', and 'certificate' keys

        Returns:
            List of NormalizedFact objects extracted from the certificate
        """
        facts: List[NormalizedFact] = []

        if not isinstance(raw_payload, dict):
            return facts

        domain = raw_payload.get("domain")
        certificate = raw_payload.get("certificate")

        if not isinstance(certificate, dict):
            return facts

        # Extract certificate subject information
        subject = certificate.get("subject", {})
        if isinstance(subject, dict):
            # Common Name (CN)
            common_name = subject.get("commonname") or subject.get("cn")
            if common_name:
                facts.append(
                    NormalizedFact(
                        fact_type=FactType.CERTIFICATE,
                        value=common_name,
                        source_connector=self.connector_name,
                        confidence=0.95,
                        metadata={
                            "field": "common_name",
                            "domain": domain,
                        },
                    )
                )

            # Organization
            org = subject.get("organizationname") or subject.get("o")
            if org:
                facts.append(
                    NormalizedFact(
                        fact_type=FactType.ORGANIZATION,
                        value=org,
                        source_connector=self.connector_name,
                        confidence=0.85,
                        metadata={
                            "field": "certificate_organization",
                            "domain": domain,
                        },
                    )
                )

            # Country
            country = subject.get("countryname") or subject.get("c")
            if country:
                facts.append(
                    NormalizedFact(
                        fact_type=FactType.LOCATION,
                        value=country,
                        source_connector=self.connector_name,
                        confidence=0.80,
                        metadata={
                            "field": "certificate_country",
                            "domain": domain,
                        },
                    )
                )

        # Extract certificate issuer information
        issuer = certificate.get("issuer", {})
        if isinstance(issuer, dict):
            issuer_org = issuer.get("organizationname") or issuer.get("o")
            issuer_cn = issuer.get("commonname") or issuer.get("cn")

            if issuer_org or issuer_cn:
                issuer_value = issuer_org or issuer_cn
                facts.append(
                    NormalizedFact(
                        fact_type=FactType.ORGANIZATION,
                        value=issuer_value,
                        source_connector=self.connector_name,
                        confidence=0.90,
                        metadata={
                            "field": "certificate_issuer",
                            "domain": domain,
                            "role": "certificate_authority",
                        },
                    )
                )

        # Extract validity dates
        not_before = self._parse_date(certificate.get("not_before"))
        if not_before:
            facts.append(
                NormalizedFact(
                    fact_type=FactType.CERTIFICATE,
                    value=not_before.isoformat(),
                    source_connector=self.connector_name,
                    occurred_at=not_before,
                    confidence=0.95,
                    metadata={
                        "field": "certificate_issued",
                        "domain": domain,
                    },
                )
            )

        not_after = self._parse_date(certificate.get("not_after"))
        if not_after:
            facts.append(
                NormalizedFact(
                    fact_type=FactType.EXPIRATION,
                    value=not_after.isoformat(),
                    source_connector=self.connector_name,
                    occurred_at=not_after,
                    confidence=0.95,
                    metadata={
                        "field": "certificate_expiration",
                        "domain": domain,
                    },
                )
            )

        # Extract Subject Alternative Names (SANs)
        sans = certificate.get("subject_alt_names", [])
        if isinstance(sans, list):
            for san in sans:
                if isinstance(san, dict):
                    san_type = san.get("type")
                    san_value = san.get("value")

                    if san_type == "DNS" and san_value:
                        facts.append(
                            NormalizedFact(
                                fact_type=FactType.DOMAIN,
                                value=san_value.lower(),
                                source_connector=self.connector_name,
                                confidence=0.90,
                                metadata={
                                    "field": "certificate_san",
                                    "san_type": san_type,
                                    "primary_domain": domain,
                                },
                            )
                        )
                    elif san_type == "IP Address" and san_value:
                        facts.append(
                            NormalizedFact(
                                fact_type=FactType.DNS_RECORD,
                                value=san_value,
                                source_connector=self.connector_name,
                                confidence=0.85,
                                metadata={
                                    "field": "certificate_san",
                                    "san_type": san_type,
                                    "primary_domain": domain,
                                },
                            )
                        )

        # Extract serial number as a certificate fact
        serial_number = certificate.get("serial_number")
        if serial_number:
            facts.append(
                NormalizedFact(
                    fact_type=FactType.CERTIFICATE,
                    value=serial_number,
                    source_connector=self.connector_name,
                    confidence=1.0,
                    metadata={
                        "field": "serial_number",
                        "domain": domain,
                    },
                )
            )

        return facts

    def _parse_date(self, value: Any) -> Optional[datetime]:
        """
        Parse a date value from various formats.

        Args:
            value: Date value (could be datetime, ISO string, or other format)

        Returns:
            Parsed datetime object or None if parsing fails
        """
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                # Try ISO format first
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass
        return None
