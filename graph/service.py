"""
graph/service.py

Service-layer scaffold for the Neo4j graph query/visualization layer
(Section 14.2 of MASTER_DESIGN.md).

This class intentionally contains NO nodes, relationships, queries,
correlation logic, or API-facing methods. Those responsibilities
belong to M4 (Entity Correlation Engine), M5 (Interactive Relationship
Graph), and the API layer (Section 15), which will build on top of
this class in later work.

GraphService exists here only as the agreed-upon extension point:
future modules should depend on an instance of GraphService (wired to
a Neo4jConnectionManager) rather than reaching for the driver directly.
"""

from .connection import Neo4jConnectionManager


class GraphService:
    """
    Placeholder service for graph-shaped operations against Neo4j.

    Intentionally empty. Future work (outside the scope of this
    infrastructure task) will add methods here for reading/writing
    unified entities and relationships, per M4/M5 in MASTER_DESIGN.md.
    """

    def __init__(self, connection_manager: Neo4jConnectionManager):
        self._connection_manager = connection_manager
