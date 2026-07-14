"""
graph/base.py

Base Neo4j client for graph operations.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    from neo4j import GraphDatabase
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False


class Neo4jClient:
    """Neo4j database client."""
    
    def __init__(self, uri: str, username: str, password: str):
        if not NEO4J_AVAILABLE:
            raise ImportError("neo4j package not installed")
        self.driver = GraphDatabase.driver(uri, auth=(username, password))
    
    def close(self):
        """Close the driver connection."""
        if self.driver:
            self.driver.close()
    
    def execute_write(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> None:
        """Execute a write transaction."""
        with self.driver.session() as session:
            session.run(query, parameters or {})
    
    def execute_read(
        self, query: str, parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute a read transaction and return results."""
        with self.driver.session() as session:
            result = session.run(query, parameters or {})
            return [dict(record) for record in result]
