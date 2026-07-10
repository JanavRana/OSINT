"""
graph/

Neo4j infrastructure package (Section 14.2 of MASTER_DESIGN.md).

Scope of this package, by design: connection configuration, driver
lifecycle management, and an empty GraphService extension point.

Out of scope (belongs to other modules per Section 11):
    - Node/relationship models
    - Cypher queries beyond a basic connectivity check
    - Entity correlation logic (M4)
    - API endpoints (Section 15)
"""

from .config import Neo4jConfig
from .connection import Neo4jConnectionManager, get_connection_manager
from .service import GraphService

__all__ = [
    "Neo4jConfig",
    "Neo4jConnectionManager",
    "get_connection_manager",
    "GraphService",
]
