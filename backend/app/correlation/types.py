from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set


@dataclass
class Evidence:
    fact_id: str
    source_connector: str
    value: Any
    occurred_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EntityRelationship:
    source_entity_id: str
    target_entity_id: str
    relationship_type: str
    confidence: float
    evidence: List[Evidence] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CorrelatedEntity:
    entity_id: str
    entity_type: str
    primary_value: str
    attributes: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    evidence: List[Evidence] = field(default_factory=list)
    related_facts: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CorrelatedEntities:
    entities: List[CorrelatedEntity] = field(default_factory=list)
    relationships: List[EntityRelationship] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
