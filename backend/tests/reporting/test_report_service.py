"""
Tests for ReportService.
"""

import uuid

import pytest
from sqlalchemy.orm import Session

from app.models.investigation import Investigation
from app.models.report import ReportStatus
from app.services.exceptions import NotFoundError
from app.services.report_service import ReportService


def test_generate_report(db_session: Session):
    """Test report generation."""
    # Create investigation
    investigation = Investigation(name="Test Investigation")
    db_session.add(investigation)
    db_session.commit()
    
    # Generate report
    service = ReportService(db_session)
    report = service.generate_report(investigation.id)
    
    assert report is not None
    assert report.investigation_id == investigation.id
    assert report.status == ReportStatus.COMPLETED
    assert report.pdf_content is not None
    assert len(report.pdf_content) > 0
    assert report.file_size > 0


def test_generate_report_investigation_not_found(db_session: Session):
    """Test report generation with nonexistent investigation."""
    service = ReportService(db_session)
    
    with pytest.raises(NotFoundError):
        service.generate_report(uuid.uuid4())


def test_get_latest_report(db_session: Session):
    """Test getting latest report."""
    # Create investigation
    investigation = Investigation(name="Test Investigation")
    db_session.add(investigation)
    db_session.commit()
    
    # Generate report
    service = ReportService(db_session)
    report1 = service.generate_report(investigation.id)
    
    # Get latest report
    latest = service.get_latest_report(investigation.id)
    
    assert latest.id == report1.id


def test_get_latest_report_not_found(db_session: Session):
    """Test getting latest report when none exists."""
    # Create investigation without report
    investigation = Investigation(name="Test Investigation")
    db_session.add(investigation)
    db_session.commit()
    
    service = ReportService(db_session)
    
    with pytest.raises(NotFoundError):
        service.get_latest_report(investigation.id)


def test_regenerate_report_overwrites_old(db_session: Session):
    """Test that regenerating overwrites old report."""
    # Create investigation
    investigation = Investigation(name="Test Investigation")
    db_session.add(investigation)
    db_session.commit()
    
    service = ReportService(db_session)
    
    # Generate first report
    report1 = service.generate_report(investigation.id)
    first_id = report1.id
    
    # Verify first report exists
    from app.models.report import Report
    first_report_check = db_session.get(Report, first_id)
    assert first_report_check is not None
    
    # Generate second report (should delete first one)
    report2 = service.generate_report(investigation.id)
    second_id = report2.id
    
    # Latest report should be the second one
    latest = service.get_latest_report(investigation.id)
    assert latest.id == second_id
    
    # First report should be deleted
    first_report_after = db_session.get(Report, first_id)
    assert first_report_after is None
