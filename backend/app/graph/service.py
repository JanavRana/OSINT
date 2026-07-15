"""
graph/service.py

Main graph service for orchestrating graph generation.
"""

from __future__ import annotations

from ..correlation.types import CorrelatedEntities
from .base import Neo4jClient
from .generator import GraphGenerator
from .mapper import GraphMapper
from .models import GraphStatistics
from .query_service import GraphQueryService
from .statistics import GraphStatisticsCalculator


class GraphService:
    """Main service for Neo4j graph generation and management."""
    
    def __init__(self, client: Neo4jClient):
        self.client = client
        self.mapper = GraphMapper()
        self.generator = GraphGenerator(client)
        self.query_service = GraphQueryService(client)
        self.statistics_calculator = GraphStatisticsCalculator(self.query_service)
    
    def generate_graph(
        self, correlated: CorrelatedEntities, investigation_id: str
    ) -> GraphStatistics:
        """Generate Neo4j graph from correlated entities."""
        nodes, relationships = self.mapper.map_to_graph(correlated)
        
        nodes_by_type = self.generator.create_nodes(nodes, investigation_id)
        rels_by_type = self.generator.create_relationships(relationships, investigation_id)
        
        return self.statistics_calculator.calculate_from_counts(
            nodes_by_type, rels_by_type
        )
    
    def update_graph(
        self, correlated: CorrelatedEntities, investigation_id: str
    ) -> GraphStatistics:
        """Update graph with new entities (incremental)."""
        return self.generate_graph(correlated, investigation_id)
    
    def get_investigation_graph(self, investigation_id: str):
        """Retrieve investigation graph."""
        return self.query_service.get_investigation_graph(investigation_id)
    
    def get_statistics(self, investigation_id: str) -> GraphStatistics:
        """Get graph statistics for an investigation."""
        return self.statistics_calculator.calculate(investigation_id)
    
    def find_connected(self, entity_id: str, max_depth: int = 2):
        """Find connected entities."""
        return self.query_service.find_connected_entities(entity_id, max_depth)
    
    def find_path(self, source_id: str, target_id: str):
        """Find shortest path between entities."""
        return self.query_service.find_shortest_path(source_id, target_id)
    
    def clear_investigation(self, investigation_id: str) -> None:
        """Delete all nodes and relationships for an investigation."""
        query = """
        MATCH (n {investigation_id: $investigation_id})
        DETACH DELETE n
        """
        self.client.execute_write(query, {"investigation_id": investigation_id})
