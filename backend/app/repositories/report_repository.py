"""
Repository for Report model operations.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.report import Report, ReportStatus


class ReportRepository:
    """Repository for Report database operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_report(
        self, investigation_id: uuid.UUID, status: ReportStatus = ReportStatus.GENERATING
    ) -> Report:
        """Create a new report record."""
        report = Report(investigation_id=investigation_id, status=status)
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return report
    
    def get_latest_report(self, investigation_id: uuid.UUID) -> Report | None:
        """Get the most recent report for an investigation."""
        stmt = (
            select(Report)
            .where(Report.investigation_id == investigation_id)
            .order_by(Report.generated_at.desc())
            .limit(1)
        )
        return self.db.scalar(stmt)
    
    def update_report(
        self,
        report_id: uuid.UUID,
        pdf_content: bytes | None = None,
        status: ReportStatus | None = None,
        error_message: str | None = None
    ) -> Report:
        """Update report with PDF content and status."""
        report = self.db.get(Report, report_id)
        if not report:
            raise ValueError(f"Report {report_id} not found")
        
        if pdf_content is not None:
            report.pdf_content = pdf_content
            report.file_size = len(pdf_content)
        if status is not None:
            report.status = status
        if error_message is not None:
            report.error_message = error_message
        
        self.db.commit()
        self.db.refresh(report)
        return report
    
    def delete_old_reports(self, investigation_id: uuid.UUID, keep_latest: int = 1) -> int:
        """Delete old reports, keeping only the most recent N."""
        # Get all reports ordered by generated_at desc
        stmt = (
            select(Report)
            .where(Report.investigation_id == investigation_id)
            .order_by(Report.generated_at.desc())
        )
        all_reports = list(self.db.scalars(stmt).all())
        
        # Keep the latest N, delete the rest
        if len(all_reports) <= keep_latest:
            return 0
        
        reports_to_delete = all_reports[keep_latest:]
        count = 0
        for report in reports_to_delete:
            self.db.delete(report)
            count += 1
        
        if count > 0:
            self.db.commit()
        
        return count
