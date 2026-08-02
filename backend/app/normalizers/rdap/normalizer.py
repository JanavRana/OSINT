"""
normalizers/rdap/normalizer.py

RDAP (Registration Data Access Protocol) normalizer.

Converts RDAP JSON responses into normalized facts.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, List

from ..base import BaseNormalizer
from ..registry import normalizer_registry
from ..types import FactType, NormalizationError, NormalizedFact


@normalizer_registry.register
class RdapNormalizer(BaseNormalizer):
    connector_name = "rdap"
    
    def normalize(self, raw_payload: Any) -> List[NormalizedFact]:
        if not isinstance(raw_payload, dict):
            raise NormalizationError(
                self.connector_name,
                f"Expected dict, got {type(raw_payload).__name__}"
            )
        
        facts: List[NormalizedFact] = []
        
        # Extract domain name
        domain = raw_payload.get("ldhName") or raw_payload.get("unicodeName")
        if domain:
            facts.append(NormalizedFact(
                fact_type=FactType.DOMAIN,
                value=domain.lower(),
                source_connector=self.connector_name,
                confidence=0.95,
            ))
        
        # Extract registration dates
        events = raw_payload.get("events", [])
        for event in events:
            event_action = event.get("eventAction", "")
            event_date_str = event.get("eventDate")
            
            if event_date_str:
                try:
                    event_date = datetime.fromisoformat(event_date_str.replace("Z", "+00:00"))
                    
                    if event_action == "registration":
                        facts.append(NormalizedFact(
                            fact_type=FactType.DOMAIN_REGISTRATION,
                            value=event_date_str,
                            source_connector=self.connector_name,
                            occurred_at=event_date,
                            confidence=0.95,
                            metadata={"field": "creation_date", "domain": domain},
                        ))
                    elif event_action == "expiration":
                        facts.append(NormalizedFact(
                            fact_type=FactType.EXPIRATION,
                            value=event_date_str,
                            source_connector=self.connector_name,
                            occurred_at=event_date,
                            confidence=0.90,
                            metadata={"field": "expiration_date", "domain": domain},
                        ))
                    elif event_action in ["last changed", "last update of RDAP database"]:
                        facts.append(NormalizedFact(
                            fact_type=FactType.GENERIC,
                            value=event_date_str,
                            source_connector=self.connector_name,
                            occurred_at=event_date,
                            confidence=0.85,
                            metadata={"field": event_action, "domain": domain},
                        ))
                except (ValueError, AttributeError):
                    pass
        
        # Extract nameservers
        nameservers = raw_payload.get("nameservers", [])
        seen_ns: set[str] = set()
        for ns in nameservers:
            ns_name = ns.get("ldhName") or ns.get("unicodeName")
            if ns_name:
                ns_lower = ns_name.lower()
                if ns_lower not in seen_ns:
                    seen_ns.add(ns_lower)
                    facts.append(NormalizedFact(
                        fact_type=FactType.NAMESERVER,
                        value=ns_lower,
                        source_connector=self.connector_name,
                        confidence=0.90,
                        metadata={"field": "nameserver", "domain": domain},
                    ))
        
        # Extract entities (registrar, contacts, etc.)
        entities = raw_payload.get("entities", [])
        for entity in entities:
            self._extract_entity_facts(entity, domain, facts)
        
        return facts
    
    def _extract_entity_facts(
        self, 
        entity: dict, 
        domain: str | None, 
        facts: List[NormalizedFact]
    ) -> None:
        """Extract facts from an RDAP entity."""
        roles = entity.get("roles", [])
        
        # Extract organization name
        vcards = entity.get("vcardArray", [])
        org_name = None
        emails: list[str] = []
        phones: list[str] = []
        
        if len(vcards) >= 2:
            vcard_properties = vcards[1]
            for prop in vcard_properties:
                if isinstance(prop, list) and len(prop) >= 4:
                    prop_name = prop[0]
                    prop_value = prop[3]
                    
                    if prop_name == "fn":
                        org_name = prop_value
                    elif prop_name == "org":
                        if isinstance(prop_value, str):
                            org_name = prop_value
                        elif isinstance(prop_value, list) and prop_value:
                            org_name = prop_value[0]
                    elif prop_name == "email":
                        if isinstance(prop_value, str):
                            emails.append(prop_value)
                    elif prop_name == "tel":
                        if isinstance(prop_value, str):
                            phones.append(prop_value)
        
        # Create registrar fact if entity has registrar role
        if org_name and "registrar" in roles:
            facts.append(NormalizedFact(
                fact_type=FactType.REGISTRAR,
                value=org_name,
                source_connector=self.connector_name,
                confidence=0.95,
                metadata={"field": "registrar", "role": "registrar", "domain": domain},
            ))
        elif org_name:
            facts.append(NormalizedFact(
                fact_type=FactType.ORGANIZATION,
                value=org_name,
                source_connector=self.connector_name,
                confidence=0.80,
                metadata={"roles": roles, "domain": domain},
            ))
        
        # Create contact facts
        for email in emails:
            facts.append(NormalizedFact(
                fact_type=FactType.EMAIL,
                value=email.lower(),
                source_connector=self.connector_name,
                confidence=0.85,
                metadata={
                    "roles": roles,
                    "domain": domain,
                    "organization": org_name,
                },
            ))
        
        for phone in phones:
            facts.append(NormalizedFact(
                fact_type=FactType.PHONE,
                value=phone,
                source_connector=self.connector_name,
                confidence=0.80,
                metadata={
                    "roles": roles,
                    "domain": domain,
                    "organization": org_name,
                },
            ))
        
        # Extract nested entities recursively
        nested_entities = entity.get("entities", [])
        for nested_entity in nested_entities:
            self._extract_entity_facts(nested_entity, domain, facts)
