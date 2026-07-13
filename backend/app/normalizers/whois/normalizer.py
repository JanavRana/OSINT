from __future__ import annotations

from datetime import datetime
from typing import Any, ClassVar, List, Optional

from ..base import BaseNormalizer
from ..registry import normalizer_registry
from ..types import NormalizedFact


@normalizer_registry.register
class WhoisNormalizer(BaseNormalizer):
    connector_name: ClassVar[str] = "whois"

    def normalize(self, raw_payload: dict) -> List[NormalizedFact]:
        facts: List[NormalizedFact] = []

        registrar = self._extract_registrar(raw_payload)
        if registrar:
            facts.append(
                NormalizedFact(
                    fact_type="registrar",
                    value=registrar,
                )
            )

        creation_date = self._extract_creation_date(raw_payload)
        if creation_date:
            facts.append(
                NormalizedFact(
                    fact_type="domain_registration",
                    value=None,
                    attributes={"creation_date": creation_date.isoformat()},
                    occurred_at=creation_date,
                )
            )

        expiration_date = self._extract_expiration_date(raw_payload)
        if expiration_date:
            facts.append(
                NormalizedFact(
                    fact_type="domain_expiration",
                    value=None,
                    attributes={"expiration_date": expiration_date.isoformat()},
                    occurred_at=expiration_date,
                )
            )

        nameservers = self._extract_nameservers(raw_payload)
        if nameservers:
            for ns in nameservers:
                facts.append(
                    NormalizedFact(
                        fact_type="nameserver",
                        value=ns,
                    )
                )

        registrant_org = self._extract_registrant_organization(raw_payload)
        if registrant_org:
            facts.append(
                NormalizedFact(
                    fact_type="registrant_organization",
                    value=registrant_org,
                )
            )

        registrant_country = self._extract_registrant_country(raw_payload)
        if registrant_country:
            facts.append(
                NormalizedFact(
                    fact_type="registrant_country",
                    value=registrant_country,
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
