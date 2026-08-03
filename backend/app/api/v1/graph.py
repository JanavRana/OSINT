"""
Graph API endpoints.
"""
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from neo4j import Session as Neo4jSession

from app.graph.service import GraphService
from app.services.exceptions import NotFoundError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/graph", tags=["graph"])


def get_neo4j_session():
    """
    Dependency for Neo4j session.
    
    TODO: Integrate with graph/connection.py Neo4jConnectionManager
    """
    raise NotImplementedError("Neo4j session dependency not yet wired")


def get_graph_service(session: Neo4jSession = Depends(get_neo4j_session)) -> GraphService:
    """Dependency for GraphService."""
    return GraphService(session)


@router.get(
    "/{investigation_id}",
    summary="Get investigation graph",
)
def get_investigation_graph(
    investigation_id: UUID,
    graph_service: GraphService = Depends(get_graph_service),
):
    """
    Retrieve full graph visualization data for an investigation.
    
    Returns nodes and edges for frontend rendering.
    """
    try:
        graph_data = graph_service.get_graph(investigation_id)
        
        return {
            "investigation_id": str(investigation_id),
            "nodes": graph_data["nodes"],
            "edges": graph_data["edges"],
            "node_count": len(graph_data["nodes"]),
            "edge_count": len(graph_data["edges"])
        }
    
    except Exception as exc:
        logger.error(f"Graph retrieval failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Graph retrieval failed"
        ) from exc


@router.get(
    "/{investigation_id}/entity/{entity_id}/connections",
    summary="Get entity connections",
)
def get_entity_connections(
    investigation_id: UUID,
    entity_id: str,
    max_depth: int = 2,
    graph_service: GraphService = Depends(get_graph_service),
):
    """
    Get all entities connected to a specific entity.
    """
    try:
        connections = graph_service.get_entity_connections(
            investigation_id,
            entity_id,
            max_depth
        )
        
        return connections
    
    except Exception as exc:
        logger.error(f"Connection query failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Connection query failed"
        ) from exc
