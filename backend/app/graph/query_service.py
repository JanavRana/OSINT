"""
graph/query_service.py

Query service for Neo4j graph operations.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .base import Neo4jClient


class GraphQueryService:
    """Service for querying Neo4j graph."""
    
    def __init__(self, client: Neo4jClient):
        self.client = client
    
    def get_investigation_graph(self, investigation_id: str) -> List[Dict[str, Any]]:
        """Retrieve all nodes and relationships for an investigation."""
        query = """
        MATCH (n {investigation_id: $investigation_id})
        OPTIONAL MATCH (n)-[r]->(m {investigation_id: $investigation_id})
        RETURN n, r, m
        """
        return self.client.execute_read(query, {"investigation_id": investigation_id})
    
    def find_connected_entities(
        self, entity_id: str, max_depth: int = 2
    ) -> List[Dict[str, Any]]:
        """Find entities connected to a given entity."""
        query = f"""
        MATCH path = (start {{node_id: $entity_id}})-[*1..{max_depth}]-(connected)
        RETURN DISTINCT connected
        """
        return self.client.execute_read(query, {"entity_id": entity_id})
    
    def find_shortest_path(
        self, source_id: str, target_id: str
    ) -> Optional[List[Dict[str, Any]]]:
        """Find shortest path between two entities."""
        query = """
        MATCH path = shortestPath(
            (source {node_id: $source_id})-[*]-(target {node_id: $target_id})
        )
        RETURN path
        """
        results = self.client.execute_read(
            query, {"source_id": source_id, "target_id": target_id}
        )
        return results if results else None
    
    def count_nodes_by_type(self, investigation_id: str) -> List[Dict[str, Any]]:
        """Count nodes by type for an investigation."""
        query = """
        MATCH (n {investigation_id: $investigation_id})
        RETURN labels(n)[0] as type, count(n) as count
        """
        return self.client.execute_read(query, {"investigation_id": investigation_id})
    
    def count_relationships_by_type(
        self, investigation_id: str
    ) -> List[Dict[str, Any]]:
        """Count relationships by type for an investigation."""
        query = """
        MATCH ()-[r {investigation_id: $investigation_id}]->()
        RETURN type(r) as type, count(r) as count
        """
        return self.client.execute_read(query, {"investigation_id": investigation_id})
