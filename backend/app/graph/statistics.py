"""
graph/statistics.py

Graph statistics calculation and aggregation.
"""

from __future__ import annotations

from typing import Dict

from .models import GraphStatistics, NodeType, RelationshipType
from .query_service import GraphQueryService


class GraphStatisticsCalculator:
    """Calculates statistics for investigation graphs."""
    
    def __init__(self, query_service: GraphQueryService):
        self.query_service = query_service
    
    def calculate(self, investigation_id: str) -> GraphStatistics:
        """Calculate statistics for an investigation graph."""
        node_results = self.query_service.count_nodes_by_type(investigation_id)
        rel_results = self.query_service.count_relationships_by_type(investigation_id)
        
        nodes_by_type = {result["type"]: result["count"] for result in node_results}
        relationships_by_type = {
            result["type"]: result["count"] for result in rel_results
        }
        
        return GraphStatistics(
            total_nodes=sum(nodes_by_type.values()),
            total_relationships=sum(relationships_by_type.values()),
            nodes_by_type=nodes_by_type,
            relationships_by_type=relationships_by_type
        )
    
    def calculate_from_counts(
        self,
        nodes_by_type: Dict[NodeType, int],
        relationships_by_type: Dict[RelationshipType, int]
    ) -> GraphStatistics:
        """Calculate statistics from generation counts."""
        return GraphStatistics(
            total_nodes=sum(nodes_by_type.values()),
            total_relationships=sum(relationships_by_type.values()),
            nodes_by_type={k.value: v for k, v in nodes_by_type.items()},
            relationships_by_type={k.value: v for k, v in relationships_by_type.items()}
        )
