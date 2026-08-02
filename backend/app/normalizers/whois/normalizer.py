from __future__ import annotations

from datetime import datetime
from typing import Any, ClassVar, List, Optional

from ..base import BaseNormalizer
from ..registry import normalizer_registry
from ..types import FactType, NormalizedFact


@normalizer_registry.register
class WhoisNormalizer(BaseNormalizer):
    connector_name: ClassVar[str] = "whois"

    def normalize(self, raw_payload: dict) -> List[NormalizedFact]:
        facts: List[NormalizedFact] = []

        registrar = self._extract_registrar(raw_payload)
        if registrar:
            facts.append(
                NormalizedFact(
                    fact_type=FactType.REGISTRAR,
                    value=registrar,
                    source_connector=self.connector_name,
                    confidence=0.95,
                    metadata={"field": "registrar"},
                )
            )

        creation_date = self._extract_creation_date(raw_payload)
        if creation_date:
            facts.append(
                NormalizedFact(
                    fact_type=FactType.DOMAIN_REGISTRATION,
                    value=creation_date.isoformat(),
                    source_connector=self.connector_name,
                    occurred_at=creation_date,
                    confidence=0.95,
                    metadata={"field": "creation_date"},
                )
            )

        expiration_date = self._extract_expiration_date(raw_payload)
        if expiration_date:
            facts.append(
                NormalizedFact(
                    fact_type=FactType.EXPIRATION,
                    value=expiration_date.isoformat(),
                    source_connector=self.connector_name,
                    occurred_at=expiration_date,
                    confidence=0.90,
                    metadata={"field": "expiration_date"},
                )
            )

        nameservers = self._extract_nameservers(raw_payload)
        if nameservers:
            for ns in nameservers:
                facts.append(
                    NormalizedFact(
                        fact_type=FactType.NAMESERVER,
                        value=ns,
                        source_connector=self.connector_name,
                        confidence=0.90,
                        metadata={"field": "nameserver"},
                    )
                )

        registrant_org = self._extract_registrant_organization(raw_payload)
        if registrant_org:
            facts.append(
                NormalizedFact(
                    fact_type=FactType.ORGANIZATION,
                    value=registrant_org,
                    source_connector=self.connector_name,
                    confidence=0.80,
                    metadata={"field": "registrant_organization"},
                )
            )

        registrant_country = self._extract_registrant_country(raw_payload)
        if registrant_country:
            facts.append(
                NormalizedFact(
                    fact_type=FactType.LOCATION,
                    value=registrant_country,
                    source_connector=self.connector_name,
                    confidence=0.75,
                    metadata={"field": "registrant_country"},
                )
            )

        # Extract emails if present
        emails = self._extract_emails(raw_payload)
        for email in emails:
            facts.append(
                NormalizedFact(
                    fact_type=FactType.EMAIL,
                    value=email,
                    source_connector=self.connector_name,
                    confidence=0.85,
                    metadata={"field": "email"},
                )
            )

        return facts

    def _extract_registrar(self, raw_payload: dict) -> Optional[str]:
        registrar = raw_payload.get("registrar")
        if isinstance(registrar, str):
            return registrar.strip() if registrar.strip() else None
        if isinstance(registrar, list) and registrar:
            first = registrar[0]
            return first.strip() if isinstance(first, str) and first.strip() else None
        return None

    def _extract_creation_date(self, raw_payload: dict) -> Optional[datetime]:
        return self._parse_date_field(raw_payload.get("creation_date"))

    def _extract_expiration_date(self, raw_payload: dict) -> Optional[datetime]:
        return self._parse_date_field(raw_payload.get("expiration_date"))

    def _parse_date_field(self, value: Any) -> Optional[datetime]:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                return None
        if isinstance(value, list) and value:
            first = value[0]
            if isinstance(first, datetime):
                return first
            if isinstance(first, str):
                try:
                    return datetime.fromisoformat(first.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    return None
        return None

    def _extract_nameservers(self, raw_payload: dict) -> List[str]:
        nameservers = raw_payload.get("name_servers", [])
        if isinstance(nameservers, str):
            nameservers = [nameservers]
        if not isinstance(nameservers, list):
            return []
        
        result = []
        for ns in nameservers:
            if isinstance(ns, str):
                cleaned = ns.strip().lower()
                if cleaned and cleaned not in result:
                    result.append(cleaned)
        return result

    def _extract_registrant_organization(self, raw_payload: dict) -> Optional[str]:
        org = raw_payload.get("org")
        if isinstance(org, str):
            return org.strip() if org.strip() else None
        if isinstance(org, list) and org:
            first = org[0]
            return first.strip() if isinstance(first, str) and first.strip() else None
        return None

    def _extract_registrant_country(self, raw_payload: dict) -> Optional[str]:
        country = raw_payload.get("country")
        if isinstance(country, str):
            return country.strip() if country.strip() else None
        if isinstance(country, list) and country:
            first = country[0]
            return first.strip() if isinstance(first, str) and first.strip() else None
        return None

    def _extract_emails(self, raw_payload: dict) -> List[str]:
        emails = raw_payload.get("emails")
        if emails is None:
            return []
        if isinstance(emails, str):
            stripped = emails.strip().lower()
            return [stripped] if stripped else []
        if isinstance(emails, list):
            result = []
            for e in emails:
                if isinstance(e, str):
                    cleaned = e.strip().lower()
                    if cleaned and cleaned not in result:
                        result.append(cleaned)
            return result
        return []
