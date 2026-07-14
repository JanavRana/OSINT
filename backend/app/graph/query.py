"""
graph/query.py

Cypher query builders for common graph operations.
"""

from __future__ import annotations


class QueryBuilder:
    """Builds Cypher queries for graph operations."""
    
    @staticmethod
    def create_node_query(node_type: str) -> str:
        """Build MERGE query for node creation."""
        return f"""
        MERGE (n:{node_type} {{node_id: $node_id}})
        ON CREATE SET n += $properties, n.investigation_id = $investigation_id
        ON MATCH SET n += $properties
        """
    
    @staticmethod
    def create_relationship_query(relationship_type: str) -> str:
        """Build MERGE query for relationship creation."""
        return f"""
        MATCH (source {{node_id: $source_id}})
        MATCH (target {{node_id: $target_id}})
        MERGE (source)-[r:{relationship_type}]->(target)
        ON CREATE SET r += $properties, r.investigation_id = $investigation_id
        ON MATCH SET r += $properties
        """
    
    @staticmethod
    def get_investigation_graph_query() -> str:
        """Build query to retrieve investigation graph."""
        return """
        MATCH (n {investigation_id: $investigation_id})
        OPTIONAL MATCH (n)-[r]->(m {investigation_id: $investigation_id})
        RETURN n, r, m
        """
    
    @staticmethod
    def count_nodes_by_type_query() -> str:
        """Build query to count nodes by type."""
        return """
        MATCH (n {investigation_id: $investigation_id})
        RETURN labels(n)[0] as type, count(n) as count
        """
    
    @staticmethod
    def count_relationships_by_type_query() -> str:
        """Build query to count relationships by type."""
        return """
        MATCH ()-[r {investigation_id: $investigation_id}]->()
        RETURN type(r) as type, count(r) as count
        """
    
    @staticmethod
    def find_connected_query(max_depth: int) -> str:
        """Build query to find connected entities."""
        return f"""
        MATCH path = (start {{node_id: $entity_id}})-[*1..{max_depth}]-(connected)
        RETURN DISTINCT connected
        """
    
    @staticmethod
    def find_shortest_path_query() -> str:
        """Build query to find shortest path."""
        return """
        MATCH path = shortestPath(
            (source {node_id: $source_id})-[*]-(target {node_id: $target_id})
        )
        RETURN path
        """
    
    @staticmethod
    def delete_investigation_query() -> str:
        """Build query to delete investigation graph."""
        return """
        MATCH (n {investigation_id: $investigation_id})
        DETACH DELETE n
        """
