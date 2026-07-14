"""
graph/generator.py

Generates Neo4j nodes and relationships from graph models.
"""

from __future__ import annotations

from typing import Dict, List

from .base import Neo4jClient
from .models import GraphNode, GraphRelationship, NodeType, RelationshipType


class GraphGenerator:
    """Generates Neo4j nodes and relationships with duplicate prevention."""
    
    def __init__(self, client: Neo4jClient):
        self.client = client
    
    def create_nodes(
        self, nodes: List[GraphNode], investigation_id: str
    ) -> Dict[NodeType, int]:
        """Create nodes in Neo4j with duplicate prevention."""
        counts: Dict[NodeType, int] = {}
        
        for node in nodes:
            self._create_node(node, investigation_id)
            counts[node.node_type] = counts.get(node.node_type, 0) + 1
        
        return counts
    
    def create_relationships(
        self, relationships: List[GraphRelationship], investigation_id: str
    ) -> Dict[RelationshipType, int]:
        """Create relationships in Neo4j with duplicate prevention."""
        counts: Dict[RelationshipType, int] = {}
        
        for rel in relationships:
            self._create_relationship(rel, investigation_id)
            counts[rel.relationship_type] = counts.get(rel.relationship_type, 0) + 1
        
        return counts
    
    def _create_node(self, node: GraphNode, investigation_id: str) -> None:
        """Create a single node using MERGE to prevent duplicates."""
        query = QueryBuilder.create_node_query(node.node_type.value)

        self.client.execute_write(
            query,
            {
                "node_id": node.node_id,
                "properties": node.properties,
                "investigation_id": investigation_id,
            },
        )
    
    def _create_relationship(
        self, rel: GraphRelationship, investigation_id: str) -> None:
        """Create a single relationship using MERGE to prevent duplicates."""
        query = QueryBuilder.create_relationship_query(
            rel.relationship_type.value
        )

        self.client.execute_write(
            query,
            {
                "source_id": rel.source_node_id,
                "target_id": rel.target_node_id,
                "properties": rel.properties,
                "investigation_id": investigation_id,
            },
        )
