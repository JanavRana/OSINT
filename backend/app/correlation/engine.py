from __future__ import annotations

import hashlib
from collections import defaultdict
from typing import Dict, List, Set, Tuple

from ..normalizers.types import NormalizedFact
from .types import CorrelatedEntities, CorrelatedEntity, EntityRelationship, Evidence


class CorrelationEngine:
    def __init__(self):
        self._entity_id_counter = 0

    def correlate(self, facts: List[NormalizedFact]) -> CorrelatedEntities:
        if not facts:
            return CorrelatedEntities()

        entities: List[CorrelatedEntity] = []
        relationships: List[EntityRelationship] = []

        value_to_entity: Dict[Tuple[str, str], CorrelatedEntity] = {}
        domain_entities: List[CorrelatedEntity] = []

        for fact in facts:
            entity = self._create_entity_from_fact(fact)
            
            if entity.entity_type == "domain":
                domain_entities.append(entity)
                value_to_entity[("domain", entity.primary_value)] = entity
            elif entity.entity_type in ["registrar", "organization", "nameserver", "country"]:
                key = (entity.entity_type, entity.primary_value)
                if key in value_to_entity:
                    existing = value_to_entity[key]
                    existing.evidence.extend(entity.evidence)
                    existing.related_facts.update(entity.related_facts)
                else:
                    entities.append(entity)
                    value_to_entity[key] = entity

        entities.extend(domain_entities)

        relationships = self._generate_relationships(facts, value_to_entity)

        return CorrelatedEntities(
            entities=entities,
            relationships=relationships,
            metadata={"total_facts_processed": len(facts)}
        )

    def _create_entity_from_fact(self, fact: NormalizedFact) -> CorrelatedEntity:
        entity_id = self._generate_entity_id(fact)
        
        fact_type_str = fact.fact_type.value if hasattr(fact.fact_type, 'value') else str(fact.fact_type)
        
        entity_type_mapping = {
            "email": "email",
            "phone": "phone",
            "username": "username",
            "domain": "domain",
            "wallet_address": "wallet",
            "domain_registration": "domain",
            "generic": self._infer_type_from_metadata(fact),
        }
        
        entity_type = entity_type_mapping.get(fact_type_str, "generic")
        
        if entity_type == "generic" and "field" in fact.metadata:
            field_name = fact.metadata["field"]
            if field_name == "registrar":
                entity_type = "registrar"
            elif field_name == "registrant_organization":
                entity_type = "organization"
            elif field_name == "nameserver":
                entity_type = "nameserver"
            elif field_name == "registrant_country":
                entity_type = "country"
        
        primary_value = str(fact.value) if fact.value is not None else ""
        
        evidence = Evidence(
            fact_id=entity_id,
            source_connector=fact.source_connector,
            value=fact.value,
            occurred_at=fact.occurred_at,
            metadata=fact.metadata.copy() if fact.metadata else {}
        )
        
        return CorrelatedEntity(
            entity_id=entity_id,
            entity_type=entity_type,
            primary_value=primary_value,
            confidence=fact.confidence,
            evidence=[evidence],
            related_facts={entity_id}
        )

    def _infer_type_from_metadata(self, fact: NormalizedFact) -> str:
        if "field" in fact.metadata:
            field_name = fact.metadata["field"]
            if "registrar" in field_name:
                return "registrar"
            elif "organization" in field_name:
                return "organization"
            elif "nameserver" in field_name:
                return "nameserver"
            elif "country" in field_name:
                return "country"
        return "generic"

    def _generate_entity_id(self, fact: NormalizedFact) -> str:
        self._entity_id_counter += 1
        fact_type_str = fact.fact_type.value if hasattr(fact.fact_type, 'value') else str(fact.fact_type)
        value_str = str(fact.value) if fact.value is not None else ""
        connector = fact.source_connector
        content = f"{fact_type_str}:{value_str}:{connector}:{self._entity_id_counter}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _generate_relationships(
        self,
        facts: List[NormalizedFact],
        value_to_entity: Dict[Tuple[str, str], CorrelatedEntity]
    ) -> List[EntityRelationship]:
        relationships: List[EntityRelationship] = []
        
        domain_to_facts: Dict[str, List[NormalizedFact]] = defaultdict(list)
        
        for fact in facts:
            if "domain" in str(fact.fact_type).lower() or fact.metadata.get("entity_type") == "domain":
                domain_key = str(fact.value) if fact.value else ""
                domain_to_facts[domain_key].append(fact)
            elif "field" in fact.metadata:
                pass
        
        for domain_value, domain_facts in domain_to_facts.items():
            domain_entity = value_to_entity.get(("domain", domain_value))
            if not domain_entity:
                continue
            
            related_facts = [f for f in facts if f not in domain_facts]
            
            for fact in related_facts:
                target_entity = self._find_entity_for_fact(fact, value_to_entity)
                if target_entity and target_entity.entity_id != domain_entity.entity_id:
                    rel_type = self._determine_relationship_type(domain_entity, target_entity)
                    confidence = self._calculate_relationship_confidence(domain_entity, target_entity, fact)
                    
                    evidence = Evidence(
                        fact_id=fact.raw_reference_id or "",
                        source_connector=fact.source_connector,
                        value=fact.value,
                        occurred_at=fact.occurred_at,
                        metadata=fact.metadata.copy() if fact.metadata else {}
                    )
                    
                    relationships.append(EntityRelationship(
                        source_entity_id=domain_entity.entity_id,
                        target_entity_id=target_entity.entity_id,
                        relationship_type=rel_type,
                        confidence=confidence,
                        evidence=[evidence]
                    ))
        
        return relationships

    def _find_entity_for_fact(
        self,
        fact: NormalizedFact,
        value_to_entity: Dict[Tuple[str, str], CorrelatedEntity]
    ) -> CorrelatedEntity:
        entity_type = self._infer_type_from_metadata(fact)
        if entity_type == "generic" and "field" in fact.metadata:
            field_name = fact.metadata["field"]
            if "registrar" in field_name:
                entity_type = "registrar"
            elif "organization" in field_name:
                entity_type = "organization"
            elif "nameserver" in field_name:
                entity_type = "nameserver"
            elif "country" in field_name:
                entity_type = "country"
        
        value_str = str(fact.value) if fact.value is not None else ""
        return value_to_entity.get((entity_type, value_str))

    def _determine_relationship_type(
        self,
        source: CorrelatedEntity,
        target: CorrelatedEntity
    ) -> str:
        if source.entity_type == "domain":
            if target.entity_type == "registrar":
                return "registered_with"
            elif target.entity_type == "organization":
                return "owned_by"
            elif target.entity_type == "nameserver":
                return "uses_nameserver"
            elif target.entity_type == "country":
                return "registered_in"
        
        return "related_to"

    def _calculate_relationship_confidence(
        self,
        source: CorrelatedEntity,
        target: CorrelatedEntity,
        fact: NormalizedFact
    ) -> float:
        base_confidence = 0.8
        
        if fact.source_connector == "whois":
            base_confidence = 0.9
        
        if source.confidence < 1.0 or target.confidence < 1.0:
            base_confidence *= min(source.confidence, target.confidence)
        
        return min(base_confidence, 1.0)
