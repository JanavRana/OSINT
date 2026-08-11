"""
reporting/report_generator.py

Main report generator for PDF investigation reports using ReportLab.
"""

from __future__ import annotations

import io
from typing import Any, Dict

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate

from .sections import (
    ConnectorSection,
    CoverPage,
    IdentifiersSection,
    TimelineSection,
)


class ReportGenerator:
    """Generates evidence-grade PDF investigation reports using ReportLab."""
    
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
            investigation_data: Dict containing investigation metadata, statistics, graph, facts, connectors, timeline
            output_path: Optional file path to save PDF
        
        Returns:
            PDF bytes
        """
        buffer = open(output_path, 'wb') if output_path else io.BytesIO()
        
        # 0.5 inch margins (36pt) for maximum clean content space
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36,
        )
        
        story = []
        
        # Page 1: Executive Summary Box + Relationship Graph
        story.extend(CoverPage().build(investigation_data))
        
        # Page 2: Extracted Identifiers & Evidence Table
        story.extend(IdentifiersSection().build(investigation_data))
        
        # Page 3: Connector Execution Log
        story.extend(ConnectorSection().build(investigation_data))
        
        # Page 4: Chronological Event Timeline
        story.extend(TimelineSection().build(investigation_data))
        
        doc.build(story)
        
        if isinstance(buffer, io.BytesIO):
            return buffer.getvalue()
        else:
            buffer.close()
            with open(output_path, 'rb') as f:
                return f.read()
