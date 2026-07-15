"""
graph/models.py

Data models for Neo4j graph generation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict


class NodeType(str, Enum):
    DOMAIN = "Domain"
    REGISTRAR = "Registrar"
    ORGANIZATION = "Organization"
    NAMESERVER = "Nameserver"
    COUNTRY = "Country"


class RelationshipType(str, Enum):
    REGISTERED_BY = "REGISTERED_BY"
    HAS_NAMESERVER = "HAS_NAMESERVER"
    LOCATED_IN = "LOCATED_IN"
    OPERATES = "OPERATES"


@dataclass
class GraphNode:
    node_type: NodeType
    node_id: str
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphRelationship:
    relationship_type: RelationshipType
    source_node_id: str
    target_node_id: str
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphStatistics:
    total_nodes: int = 0
    total_relationships: int = 0
    nodes_by_type: Dict[str, int] = field(default_factory=dict)
    relationships_by_type: Dict[str, int] = field(default_factory=dict)
