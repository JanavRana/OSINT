"""
Graph service for Neo4j entity/relationship synchronization.
"""
import logging
from typing import List, Dict, Any, Optional
from uuid import UUID

from neo4j import Session
from neo4j.exceptions import Neo4jError

from ..correlation.types import CorrelatedEntity, EntityRelationship, CorrelatedEntities

logger = logging.getLogger(__name__)


class GraphService:
    """
    Service for syncing correlated entities and relationships to Neo4j.
    
    PostgreSQL remains the source of truth. Neo4j is a query/visualization layer.
    """
    
    def __init__(self, session: Session):
        self._session = session
    
    def sync_investigation(
        self,
        investigation_id: UUID,
        entities: CorrelatedEntities
    ) -> None:
        """
        Sync an investigation's entities and relationships to Neo4j.
        
        Replaces any existing graph data for this investigation.
        """
        try:
            self._clear_investigation(investigation_id)
            
            self._create_entities(investigation_id, entities.entities)
            
            self._create_relationships(investigation_id, entities.relationships)
            
            logger.info(
                f"Synced investigation {investigation_id}: "
                f"{len(entities.entities)} entities, "
                f"{len(entities.relationships)} relationships"
            )
        
        except Neo4jError as e:
            logger.error(f"Neo4j sync failed: {e}")
            raise
    
    def _clear_investigation(self, investigation_id: UUID) -> None:
        """Remove all nodes/edges for an investigation."""
        query = """
        MATCH (n {investigation_id: $investigation_id})
        DETACH DELETE n
        """
        self._session.run(query, investigation_id=str(investigation_id))
    
    def _create_entities(
        self,
        investigation_id: UUID,
        entities: List[CorrelatedEntity]
    ) -> None:
        """Create entity nodes."""
        for entity in entities:
            query = """
            CREATE (e:Entity {
                entity_id: $entity_id,
                investigation_id: $investigation_id,
                entity_type: $entity_type,
                primary_value: $primary_value,
                confidence: $confidence,
                evidence_count: $evidence_count
            })
            """
            self._session.run(
                query,
                entity_id=entity.entity_id,
                investigation_id=str(investigation_id),
                entity_type=entity.entity_type,
                primary_value=entity.primary_value,
                confidence=entity.confidence,
                evidence_count=len(entity.evidence)
            )
    
    def _create_relationships(
        self,
        investigation_id: UUID,
        relationships: List[EntityRelationship]
    ) -> None:
        """Create relationship edges."""
        for rel in relationships:
            query = """
            MATCH (source:Entity {entity_id: $source_id, investigation_id: $investigation_id})
            MATCH (target:Entity {entity_id: $target_id, investigation_id: $investigation_id})
            CREATE (source)-[r:RELATED {
                relationship_type: $rel_type,
                confidence: $confidence,
                evidence_count: $evidence_count
            }]->(target)
            """
            self._session.run(
                query,
                source_id=rel.source_entity_id,
                target_id=rel.target_entity_id,
                investigation_id=str(investigation_id),
                rel_type=rel.relationship_type,
                confidence=rel.confidence,
                evidence_count=len(rel.evidence)
            )
    
    def get_graph(self, investigation_id: UUID) -> Dict[str, Any]:
        """
        Retrieve full graph for an investigation.
        
        Returns dict with nodes and edges for frontend visualization.
        """
        try:
            nodes_query = """
            MATCH (n:Entity {investigation_id: $investigation_id})
            RETURN n.entity_id AS id, 
                   n.entity_type AS type,
                   n.primary_value AS label,
                   n.confidence AS confidence,
                   n.evidence_count AS evidence_count
            """
            
            edges_query = """
            MATCH (s:Entity {investigation_id: $investigation_id})-[r:RELATED]->(t:Entity)
            RETURN s.entity_id AS source,
                   t.entity_id AS target,
                   r.relationship_type AS type,
                   r.confidence AS confidence,
                   r.evidence_count AS evidence_count
            """
            
            nodes_result = self._session.run(nodes_query, investigation_id=str(investigation_id))
            edges_result = self._session.run(edges_query, investigation_id=str(investigation_id))
            
            nodes = [dict(record) for record in nodes_result]
            edges = [dict(record) for record in edges_result]
            
            return {
                "nodes": nodes,
                "edges": edges
            }
        
        except Neo4jError as e:
            logger.error(f"Graph retrieval failed: {e}")
            return {"nodes": [], "edges": []}
    
    def get_entity_connections(
        self,
        investigation_id: UUID,
        entity_id: str,
        max_depth: int = 2
    ) -> Dict[str, Any]:
        """
        Get all entities connected to a specific entity within max_depth hops.
        """
        try:
            query = """
            MATCH path = (start:Entity {entity_id: $entity_id, investigation_id: $investigation_id})
                         -[:RELATED*1..%d]-(connected:Entity)
            RETURN DISTINCT connected.entity_id AS id,
                            connected.entity_type AS type,
                            connected.primary_value AS label,
                            connected.confidence AS confidence
            """ % max_depth
            
            result = self._session.run(
                query,
                entity_id=entity_id,
                investigation_id=str(investigation_id)
            )
            
            connections = [dict(record) for record in result]
            
            return {
                "entity_id": entity_id,
                "connections": connections,
                "count": len(connections)
            }
        
        except Neo4jError as e:
            logger.error(f"Connection query failed: {e}")
            return {"entity_id": entity_id, "connections": [], "count": 0}
    
    def find_shared_entities(
        self,
        investigation_ids: List[UUID]
    ) -> List[Dict[str, Any]]:
        """
        Find entities that appear in multiple investigations.
        Used for cross-investigation correlation.
        """
        try:
            query = """
            MATCH (e:Entity)
            WHERE e.investigation_id IN $investigation_ids
            WITH e.entity_type AS type, e.primary_value AS value, 
                 COLLECT(DISTINCT e.investigation_id) AS investigations
            WHERE SIZE(investigations) > 1
            RETURN type, value, investigations, SIZE(investigations) AS count
            ORDER BY count DESC
            """
            
            result = self._session.run(
                query,
                investigation_ids=[str(inv_id) for inv_id in investigation_ids]
            )
            
            return [dict(record) for record in result]
        
        except Neo4jError as e:
            logger.error(f"Shared entity query failed: {e}")
            return []
