"""
Report service for PDF generation and management.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.models.report import Report, ReportStatus
from app.models.seed_identifier import SeedIdentifier
from app.repositories.connector_result_repository import ConnectorResultRepository
from app.repositories.investigation_repository import InvestigationRepository
from app.repositories.normalized_fact_repository import NormalizedFactRepository
from app.repositories.report_repository import ReportRepository
from app.reporting.report_generator import ReportGenerator
from app.services.exceptions import NotFoundError
from app.timeline.service import TimelineService

logger = logging.getLogger(__name__)


class ReportService:
    """Service for PDF report generation and retrieval."""
    
    def __init__(self, db: Session):
        self.db = db
        self.report_repo = ReportRepository(db)
        self.investigation_repo = InvestigationRepository(db)
        self.generator = ReportGenerator()
    
    def generate_report(
        self,
        investigation_id: uuid.UUID,
        graph_image_base64: Optional[str] = None
    ) -> Report:
        """
        Generate PDF report for an investigation.
        
        Overwrites previous report by deleting old ones before creating new.
        """
        investigation = self.investigation_repo.get_by_id(investigation_id)
        if not investigation:
            raise NotFoundError(f"Investigation {investigation_id} not found")
        
        # Delete old reports first
        self.report_repo.delete_old_reports(investigation_id, keep_latest=0)
        
        # Create report record
        report = self.report_repo.create_report(investigation_id)
        
        try:
            # Collect real investigation data from DB
            investigation_data = self._collect_investigation_data(
                investigation_id,
                graph_image_base64=graph_image_base64
            )
            
            # Generate PDF
            pdf_bytes = self.generator.generate_report(investigation_data)
            
            # Update report with PDF content
            report = self.report_repo.update_report(
                report.id,
                pdf_content=pdf_bytes,
                status=ReportStatus.COMPLETED
            )
            
            logger.info(f"Report generated successfully for investigation {investigation_id}")
            
        except Exception as exc:
            logger.error(f"Report generation failed: {exc}", exc_info=True)
            self.report_repo.update_report(
                report.id,
                status=ReportStatus.FAILED,
                error_message=str(exc)
            )
            raise
        
        return report
    
    def get_latest_report(self, investigation_id: uuid.UUID) -> Report:
        """Get the most recent report for an investigation."""
        investigation = self.investigation_repo.get_by_id(investigation_id)
        if not investigation:
            raise NotFoundError(f"Investigation {investigation_id} not found")
        
        report = self.report_repo.get_latest_report(investigation_id)
        if not report:
            raise NotFoundError(f"No report found for investigation {investigation_id}")
        
        return report
    
    def _collect_investigation_data(
        self,
        investigation_id: uuid.UUID,
        graph_image_base64: Optional[str] = None
    ) -> Dict[str, Any]:
        """Collect real investigation facts, connector results, seed data, and timeline events."""
        investigation = self.investigation_repo.get_by_id(investigation_id)
        
        # Seed identifier
        seed = self.db.query(SeedIdentifier).filter(
            SeedIdentifier.investigation_id == investigation_id
        ).first()

        # Connectors
        connector_repo = ConnectorResultRepository(self.db)
        connectors_raw = connector_repo.list_by_investigation(investigation_id)

        # Facts
        fact_repo = NormalizedFactRepository(self.db)
        facts_raw = fact_repo.list_by_investigation(investigation_id)

        # Timeline
        timeline_events = TimelineService(self.db).get_timeline(investigation_id)

        # Calculate metrics
        avg_conf = (
            sum(f.confidence for f in facts_raw) / len(facts_raw)
            if facts_raw else 0.0
        )
        
        # Process connectors raw_response dictionary safely
        connectors_data = []
        successful_cnt = 0
        for c in connectors_raw:
            raw = c.raw_response if isinstance(c.raw_response, dict) else {}
            err = raw.get("error")
            c_status = "failed" if err else (raw.get("status") or "success")
            if c_status == "success":
                successful_cnt += 1
            
            dur = raw.get("execution_duration_seconds") or raw.get("duration")
            dur_str = f"{dur:.2f}s" if isinstance(dur, (int, float)) else "0.50s"
            started_str = c.created_at.strftime("%H:%M:%S") if c.created_at else "N/A"
            
            connectors_data.append({
                "name": c.connector_name,
                "status": c_status,
                "started_at": started_str,
                "duration": dur_str,
                "error": err,
            })

        return {
            "investigation": {
                "id": str(investigation.id),
                "name": investigation.name,
                "status": getattr(investigation.status, 'value', str(investigation.status)),
                "created_at": investigation.created_at.strftime("%Y-%m-%d %H:%M:%S") if investigation.created_at else "N/A",
                "updated_at": investigation.updated_at.strftime("%Y-%m-%d %H:%M:%S") if investigation.updated_at else "N/A",
                "seed_value": seed.value if seed else "N/A",
                "seed_type": getattr(seed, 'type', 'N/A') if seed else "N/A",
            },
            "statistics": {
                "total_connectors": len(connectors_raw),
                "successful_connectors": successful_cnt,
                "total_facts": len(facts_raw),
                "average_confidence": avg_conf,
            },
            "graph_image_base64": graph_image_base64,
            "connectors": connectors_data,
            "facts": [
                {
                    "id": str(f.id),
                    "type": getattr(f.fact_type, 'value', str(f.fact_type)),
                    "value": str(f.value),
                    "confidence": f.confidence,
                    "connector": f.connector_name,
                    "metadata": f.fact_metadata or {},
                }
                for f in facts_raw
            ],
            "timeline": [
                {
                    "date": e.occurred_at.strftime("%Y-%m-%d %H:%M:%S") if e.occurred_at else "N/A",
                    "title": e.title,
                    "description": e.description,
                    "connector": e.connector,
                }
                for e in timeline_events
            ],
        }
