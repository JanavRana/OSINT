"""
Report service for PDF generation and management.
"""

import logging
import uuid
from typing import Any, Dict

from sqlalchemy.orm import Session

from app.models.report import Report, ReportStatus
from app.repositories.investigation_repository import InvestigationRepository
from app.repositories.report_repository import ReportRepository
from app.reporting.report_generator import ReportGenerator
from app.services.exceptions import NotFoundError

logger = logging.getLogger(__name__)


class ReportService:
    """Service for PDF report generation and retrieval."""
    
    def __init__(self, db: Session):
        self.db = db
        self.report_repo = ReportRepository(db)
        self.investigation_repo = InvestigationRepository(db)
        self.generator = ReportGenerator()
    
    def generate_report(self, investigation_id: uuid.UUID) -> Report:
        """
        Generate PDF report for an investigation.
        
        Overwrites previous report by deleting old ones before creating new.
        """
        # Verify investigation exists
        investigation = self.investigation_repo.get_by_id(investigation_id)
        if not investigation:
            raise NotFoundError(f"Investigation {investigation_id} not found")
        
        # Delete old reports first
        self.report_repo.delete_old_reports(investigation_id, keep_latest=0)
        
        # Create report record
        report = self.report_repo.create_report(investigation_id)
        
        try:
            # Collect investigation data
            investigation_data = self._collect_investigation_data(investigation_id)
            
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
        # Verify investigation exists
        investigation = self.investigation_repo.get_by_id(investigation_id)
        if not investigation:
            raise NotFoundError(f"Investigation {investigation_id} not found")
        
        report = self.report_repo.get_latest_report(investigation_id)
        if not report:
            raise NotFoundError(f"No report found for investigation {investigation_id}")
        
        return report
    
    def _collect_investigation_data(self, investigation_id: uuid.UUID) -> Dict[str, Any]:
        """Collect all data needed for report generation."""
        investigation = self.investigation_repo.get_by_id(investigation_id)
        
        # Basic investigation data
        data = {
            'investigation': {
                'id': str(investigation.id),
                'name': investigation.name,
                'status': investigation.status.value,
                'created_at': investigation.created_at.isoformat(),
                'updated_at': investigation.updated_at.isoformat(),
            },
            'statistics': {
                'total_connectors': 0,
                'total_facts': 0,
                'total_entities': 0,
                'total_relationships': 0,
            },
            'connectors': [],
            'entities': [],
            'relationships': [],
            'timeline': [],
            'evidence': [],
            'sources': [],
            'confidence_summary': {
                'average': 0,
                'high_count': 0,
                'medium_count': 0,
                'low_count': 0,
            },
        }
        
        # TODO: Fetch actual data from repositories when correlation/timeline modules are implemented
        # For now, returning basic structure
        
        return data
