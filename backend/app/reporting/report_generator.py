"""
reporting/report_generator.py

Main report generator for PDF investigation reports.
"""

from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate

from .sections import (
    ConfidenceSection,
    ConnectorSection,
    CoverPage,
    EvidenceSection,
    ExecutiveSummary,
    InvestigationMetadata,
    RelationshipSection,
    SourcesSection,
    TimelineSection,
    UnifiedEntitiesSection,
)


class ReportGenerator:
    """Generates PDF investigation reports using ReportLab."""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
    
    def generate_report(
        self,
        investigation_data: Dict[str, Any],
        output_path: str | None = None
    ) -> bytes:
        """
        Generate PDF report for an investigation.
        
        Args:
            investigation_data: Dict containing all investigation data
            output_path: Optional file path to save PDF
        
        Returns:
            PDF bytes
        """
        if output_path:
            buffer = open(output_path, 'wb')
        else:
            buffer = io.BytesIO()
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18,
        )
        
        story = []
        
        # Build report sections
        story.extend(CoverPage().build(investigation_data))
        story.extend(ExecutiveSummary().build(investigation_data))
        story.extend(InvestigationMetadata().build(investigation_data))
        story.extend(ConnectorSection().build(investigation_data))
        story.extend(UnifiedEntitiesSection().build(investigation_data))
        story.extend(RelationshipSection().build(investigation_data))
        story.extend(TimelineSection().build(investigation_data))
        story.extend(EvidenceSection().build(investigation_data))
        story.extend(SourcesSection().build(investigation_data))
        story.extend(ConfidenceSection().build(investigation_data))
        
        doc.build(story)
        
        if isinstance(buffer, io.BytesIO):
            return buffer.getvalue()
        else:
            buffer.close()
            with open(output_path, 'rb') as f:
                return f.read()
