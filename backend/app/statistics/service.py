"""
Statistics service for aggregate metrics.
"""
import logging
from typing import Dict, List, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from ..models.investigation import Investigation

logger = logging.getLogger(__name__)


class StatisticsService:
    """
    Aggregate statistics across investigations.
    """
    
    def __init__(self, db: Session):
        self._db = db
    
    def get_overview_stats(self) -> Dict[str, Any]:
        """
        Get high-level platform statistics.
        """
        try:
            total_investigations = self._db.query(func.count(Investigation.id)).scalar()
            
            completed_investigations = (
                self._db.query(func.count(Investigation.id))
                .filter(Investigation.status == "completed")
                .scalar()
            )
            
            recent_investigations = (
                self._db.query(func.count(Investigation.id))
                .filter(Investigation.created_at >= datetime.utcnow() - timedelta(days=30))
                .scalar()
            )
            
            return {
                "total_investigations": total_investigations or 0,
                "completed_investigations": completed_investigations or 0,
                "recent_investigations": recent_investigations or 0,
                "completion_rate": (
                    round((completed_investigations / total_investigations) * 100, 2)
                    if total_investigations > 0 else 0.0
                )
            }
        except Exception as e:
            logger.error(f"Overview stats failed: {e}")
            return {
                "total_investigations": 0,
                "completed_investigations": 0,
                "recent_investigations": 0,
                "completion_rate": 0.0
            }
    
    def get_connector_stats(self) -> List[Dict[str, Any]]:
        """
        Connector success rates and usage statistics.
        
        Requires connector execution records to be persisted.
        """
        # Placeholder - requires connector_executions table
        return [
            {
                "connector_name": "whois",
                "total_executions": 0,
                "successful_executions": 0,
                "failed_executions": 0,
                "success_rate": 0.0,
                "avg_duration_seconds": 0.0
            }
        ]
    
    def get_entity_type_distribution(self) -> List[Dict[str, Any]]:
        """
        Distribution of entity types across all investigations.
        
        Requires correlation results to be persisted.
        """
        # Placeholder - requires unified_entities table
        return []
    
    def get_top_domains(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Most frequently appearing domains across investigations."""
        # Placeholder - requires normalized_facts or entities table
        return []
    
    def get_top_registrars(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Most frequently appearing registrars."""
        # Placeholder
        return []
    
    def get_top_countries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Most frequently appearing countries."""
        # Placeholder
        return []
    
    def get_investigation_duration_stats(self) -> Dict[str, Any]:
        """
        Statistics on investigation execution time.
        """
        try:
            investigations = (
                self._db.query(Investigation)
                .filter(Investigation.finished_at.isnot(None))
                .all()
            )
            
            if not investigations:
                return {
                    "avg_duration_seconds": 0.0,
                    "min_duration_seconds": 0.0,
                    "max_duration_seconds": 0.0,
                    "total_investigations": 0
                }
            
            durations = [
                (inv.finished_at - inv.started_at).total_seconds()
                for inv in investigations
                if inv.started_at and inv.finished_at
            ]
            
            if not durations:
                return {
                    "avg_duration_seconds": 0.0,
                    "min_duration_seconds": 0.0,
                    "max_duration_seconds": 0.0,
                    "total_investigations": 0
                }
            
            return {
                "avg_duration_seconds": round(sum(durations) / len(durations), 2),
                "min_duration_seconds": round(min(durations), 2),
                "max_duration_seconds": round(max(durations), 2),
                "total_investigations": len(durations)
            }
        
        except Exception as e:
            logger.error(f"Duration stats failed: {e}")
            return {
                "avg_duration_seconds": 0.0,
                "min_duration_seconds": 0.0,
                "max_duration_seconds": 0.0,
                "total_investigations": 0
            }
    
    def get_time_series_stats(
        self,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Investigation creation timeline.
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            investigations = (
                self._db.query(
                    func.date(Investigation.created_at).label('date'),
                    func.count(Investigation.id).label('count')
                )
                .filter(Investigation.created_at >= start_date)
                .group_by(func.date(Investigation.created_at))
                .order_by(desc('date'))
                .all()
            )
            
            return [
                {
                    "date": str(inv.date),
                    "count": inv.count
                }
                for inv in investigations
            ]
        
        except Exception as e:
            logger.error(f"Time series stats failed: {e}")
            return []
