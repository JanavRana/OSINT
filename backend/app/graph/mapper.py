"""
graph/mapper.py

Maps CorrelatedEntities to graph nodes and relationships.
"""

from __future__ import annotations

from typing import List, Tuple

from ..correlation.types import CorrelatedEntities, CorrelatedEntity
from .models import GraphNode, GraphRelationship, NodeType, RelationshipType


class GraphMapper:
    """Maps correlated entities to graph structures."""
    
    def map_to_graph(
        self, correlated: CorrelatedEntities
    ) -> Tuple[List[GraphNode], List[GraphRelationship]]:
        """Map CorrelatedEntities to nodes and relationships."""
        nodes: List[GraphNode] = []
        relationships: List[GraphRelationship] = []
        
        for entity in correlated.entities:
            entity_nodes, entity_rels = self._map_entity(entity)
            nodes.extend(entity_nodes)
            relationships.extend(entity_rels)
        
        return nodes, relationships
    
    def _map_entity(
        self, entity: CorrelatedEntity
    ) -> Tuple[List[GraphNode], List[GraphRelationship]]:
        """Map a single entity to nodes and relationships."""
        nodes: List[GraphNode] = []
        relationships: List[GraphRelationship] = []
        
        # Map primary entity node
        primary_node = self._create_primary_node(entity)
        if primary_node:
            nodes.append(primary_node)
        
        # Extract additional nodes and relationships from attributes
        attr_nodes, attr_rels = self._extract_from_attributes(entity)
        nodes.extend(attr_nodes)
        relationships.extend(attr_rels)
        
        return nodes, relationships
    
    def _create_primary_node(self, entity: CorrelatedEntity) -> GraphNode | None:
        """Create primary node from entity."""
        node_type = self._map_to_node_type(entity.entity_type)
        if not node_type:
            return None
        
        properties = {
            "primary_value": entity.primary_value,
            "confidence": entity.confidence,
        }
        
        for key, value in entity.attributes.items():
            if isinstance(value, (str, int, float, bool)):
                properties[key] = value
        
        return GraphNode(
            node_type=node_type,
            node_id=entity.entity_id,
            properties=properties
        )
    
    def _extract_from_attributes(
        self, entity: CorrelatedEntity
    ) -> Tuple[List[GraphNode], List[GraphRelationship]]:
        """Extract nodes and relationships from entity attributes."""
        nodes: List[GraphNode] = []
        relationships: List[GraphRelationship] = []
        
        # Registrar
        if "registrar" in entity.attributes:
            registrar = entity.attributes["registrar"]
            if isinstance(registrar, str):
                registrar_id = self._sanitize_id(f"registrar_{registrar}")
                nodes.append(GraphNode(
                    node_type=NodeType.REGISTRAR,
                    node_id=registrar_id,
                    properties={"name": registrar}
                ))
                relationships.append(GraphRelationship(
                    relationship_type=RelationshipType.REGISTERED_BY,
                    source_node_id=entity.entity_id,
                    target_node_id=registrar_id
                ))
        
        # Nameservers
        if "nameservers" in entity.attributes:
            nameservers = entity.attributes["nameservers"]
            if isinstance(nameservers, list):
                for ns in nameservers:
                    if isinstance(ns, str):
                        ns_id = self._sanitize_id(f"ns_{ns}")
                        nodes.append(GraphNode(
                            node_type=NodeType.NAMESERVER,
                            node_id=ns_id,
                            properties={"hostname": ns}
                        ))
                        relationships.append(GraphRelationship(
                            relationship_type=RelationshipType.HAS_NAMESERVER,
                            source_node_id=entity.entity_id,
                            target_node_id=ns_id
                        ))
        
        # Country
        if "country" in entity.attributes:
            country = entity.attributes["country"]
            if isinstance(country, str):
                country_id = f"country_{country.lower()}"
                nodes.append(GraphNode(
                    node_type=NodeType.COUNTRY,
                    node_id=country_id,
                    properties={"code": country}
                ))
                relationships.append(GraphRelationship(
                    relationship_type=RelationshipType.LOCATED_IN,
                    source_node_id=entity.entity_id,
                    target_node_id=country_id
                ))
        
        # Organization
        if "organization" in entity.attributes:
            org = entity.attributes["organization"]
            if isinstance(org, str):
                org_id = self._sanitize_id(f"org_{org}")
                nodes.append(GraphNode(
                    node_type=NodeType.ORGANIZATION,
                    node_id=org_id,
                    properties={"name": org}
                ))
                relationships.append(GraphRelationship(
                    relationship_type=RelationshipType.OPERATES,
                    source_node_id=entity.entity_id,
                    target_node_id=org_id
                ))
        
        return nodes, relationships
    
    def _map_to_node_type(self, entity_type: str) -> NodeType | None:
        """Map entity type string to NodeType."""
        mapping = {
            "domain": NodeType.DOMAIN,
            "registrar": NodeType.REGISTRAR,
            "organization": NodeType.ORGANIZATION,
            "nameserver": NodeType.NAMESERVER,
            "country": NodeType.COUNTRY,
        }
        return mapping.get(entity_type.lower())
    
    def _sanitize_id(self, value: str) -> str:
        """Sanitize value for node ID."""
        return value.lower().replace(" ", "_").replace(".", "_").replace("@", "_at_")
