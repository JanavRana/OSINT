"""
Global search service across investigations.
"""
import logging
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from ..models.investigation import Investigation
from ..normalizers.types import NormalizedFact

logger = logging.getLogger(__name__)


class SearchService:
    """
    Search across investigations, entities, and normalized facts.
    """
    
    def __init__(self, db: Session):
        self._db = db
    
    def search(
        self,
        query: str,
        search_type: str = "all",
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Global search across investigations.
        
        Args:
            query: Search term
            search_type: "all", "investigations", "identifiers", "facts"
            limit: Max results per category
        
        Returns:
            {
                "query": str,
                "investigations": List[Dict],
                "identifiers": List[Dict],
                "facts": List[Dict],
                "total_results": int
            }
        """
        results = {
            "query": query,
            "investigations": [],
            "identifiers": [],
            "facts": [],
            "total_results": 0
        }
        
        if search_type in ["all", "investigations"]:
            results["investigations"] = self._search_investigations(query, limit)
        
        if search_type in ["all", "identifiers"]:
            results["identifiers"] = self._search_identifiers(query, limit)
        
        if search_type in ["all", "facts"]:
            results["facts"] = self._search_facts(query, limit)
        
        results["total_results"] = (
            len(results["investigations"]) +
            len(results["identifiers"]) +
            len(results["facts"])
        )
        
        return results
    
    def _search_investigations(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Search investigations by name."""
        try:
            investigations = (
                self._db.query(Investigation)
                .filter(Investigation.name.ilike(f"%{query}%"))
                .limit(limit)
                .all()
            )
            
            return [
                {
                    "id": str(inv.id),
                    "name": inv.name,
                    "status": inv.status,
                    "created_at": inv.created_at.isoformat(),
                    "type": "investigation"
                }
                for inv in investigations
            ]
        except Exception as e:
            logger.error(f"Investigation search failed: {e}")
            return []
    
    def _search_identifiers(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Search by identifier value across all investigations."""
        # This would query the identifiers table when it exists
        # For now, placeholder
        return []
    
    def _search_facts(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Search normalized facts by value."""
        # This would query the normalized_facts table when it exists
        # For now, placeholder
        return []
    
    def search_by_entity_type(
        self,
        entity_type: str,
        value: str = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search entities by type across all investigations.
        
        Args:
            entity_type: domain, registrar, organization, etc.
            value: Optional value filter
            limit: Max results
        """
        # Placeholder for when correlation results are persisted
        return []
    
    def find_related_investigations(
        self,
        identifier_value: str
    ) -> List[Dict[str, Any]]:
        """
        Find all investigations containing a specific identifier.
        Used for cross-investigation pivoting.
        """
        # Placeholder for cross-investigation correlation
        return []
