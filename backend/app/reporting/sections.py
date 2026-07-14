"""
reporting/sections.py

Report section builders for PDF generation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


class BaseSection:
    """Base class for report sections."""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles."""
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=30,
            alignment=TA_CENTER,
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionHeading',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=12,
            spaceBefore=12,
        ))
        
        self.styles.add(ParagraphStyle(
            name='SubHeading',
            parent=self.styles['Heading3'],
            fontSize=12,
            textColor=colors.HexColor('#34495e'),
            spaceAfter=6,
        ))
    
    def build(self, data: Dict[str, Any]) -> List:
        """Build section content. Override in subclasses."""
        return []


class CoverPage(BaseSection):
    """Cover page section."""
    
    def build(self, data: Dict[str, Any]) -> List:
        story = []
        
        story.append(Spacer(1, 2*inch))
        story.append(Paragraph(
            "OSINT Intelligence Aggregator",
            self.styles['CustomTitle']
        ))
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph(
            "Investigation Report",
            self.styles['Heading2']
        ))
        story.append(Spacer(1, 0.5*inch))
        
        investigation = data.get('investigation', {})
        story.append(Paragraph(
            f"<b>Investigation:</b> {investigation.get('name', 'N/A')}",
            self.styles['Normal']
        ))
        story.append(Spacer(1, 0.2*inch))
        story.append(Paragraph(
            f"<b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            self.styles['Normal']
        ))
        
        story.append(PageBreak())
        return story


class ExecutiveSummary(BaseSection):
    """Executive summary section."""
    
    def build(self, data: Dict[str, Any]) -> List:
        story = []
        
        story.append(Paragraph("Executive Summary", self.styles['SectionHeading']))
        story.append(Spacer(1, 0.2*inch))
        
        investigation = data.get('investigation', {})
        stats = data.get('statistics', {})
        
        summary_text = f"""
        This report presents findings from investigation <b>{investigation.get('name', 'N/A')}</b>, 
        conducted using the OSINT Intelligence Aggregator platform. The investigation 
        executed {stats.get('total_connectors', 0)} connectors, extracted 
        {stats.get('total_facts', 0)} normalized facts, and identified 
        {stats.get('total_entities', 0)} unified entities with 
        {stats.get('total_relationships', 0)} relationships.
        """
        
        story.append(Paragraph(summary_text, self.styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        return story


class InvestigationMetadata(BaseSection):
    """Investigation metadata section."""
    
    def build(self, data: Dict[str, Any]) -> List:
        story = []
        
        story.append(Paragraph("Investigation Metadata", self.styles['SectionHeading']))
        story.append(Spacer(1, 0.2*inch))
        
        investigation = data.get('investigation', {})
        
        metadata_data = [
            ['Field', 'Value'],
            ['Investigation ID', str(investigation.get('id', 'N/A'))],
            ['Name', investigation.get('name', 'N/A')],
            ['Status', investigation.get('status', 'N/A')],
            ['Created', investigation.get('created_at', 'N/A')],
            ['Updated', investigation.get('updated_at', 'N/A')],
        ]
        
        table = Table(metadata_data, colWidths=[2*inch, 4*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        
        story.append(table)
        story.append(Spacer(1, 0.3*inch))
        
        return story


class ConnectorSection(BaseSection):
    """Connector execution summary section."""
    
    def build(self, data: Dict[str, Any]) -> List:
        story = []
        
        story.append(Paragraph("Connector Execution Summary", self.styles['SectionHeading']))
        story.append(Spacer(1, 0.2*inch))
        
        connectors = data.get('connectors', [])
        
        if not connectors:
            story.append(Paragraph("No connector executions recorded.", self.styles['Normal']))
            story.append(Spacer(1, 0.3*inch))
            return story
        
        connector_data = [['Connector', 'Status', 'Started', 'Duration']]
        
        for connector in connectors:
            connector_data.append([
                connector.get('name', 'N/A'),
                connector.get('status', 'N/A'),
                connector.get('started_at', 'N/A'),
                connector.get('duration', 'N/A'),
            ])
        
        table = Table(connector_data, colWidths=[1.5*inch, 1*inch, 2*inch, 1.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        
        story.append(table)
        story.append(Spacer(1, 0.3*inch))
        
        return story


class UnifiedEntitiesSection(BaseSection):
    """Unified entities section."""
    
    def build(self, data: Dict[str, Any]) -> List:
        story = []
        
        story.append(Paragraph("Unified Entities", self.styles['SectionHeading']))
        story.append(Spacer(1, 0.2*inch))
        
        entities = data.get('entities', [])
        
        if not entities:
            story.append(Paragraph("No entities identified.", self.styles['Normal']))
            story.append(Spacer(1, 0.3*inch))
            return story
        
        for entity in entities:
            story.append(Paragraph(
                f"<b>{entity.get('type', 'Entity')}: {entity.get('value', 'N/A')}</b>",
                self.styles['SubHeading']
            ))
            story.append(Paragraph(
                f"Confidence: {entity.get('confidence', 0):.2f}",
                self.styles['Normal']
            ))
            
            attributes = entity.get('attributes', {})
            if attributes:
                story.append(Paragraph("Attributes:", self.styles['Normal']))
                for key, value in attributes.items():
                    story.append(Paragraph(
                        f"  • {key}: {value}",
                        self.styles['Normal']
                    ))
            
            story.append(Spacer(1, 0.2*inch))
        
        return story


class RelationshipSection(BaseSection):
    """Relationship summary section."""
    
    def build(self, data: Dict[str, Any]) -> List:
        story = []
        
        story.append(Paragraph("Relationship Summary", self.styles['SectionHeading']))
        story.append(Spacer(1, 0.2*inch))
        
        relationships = data.get('relationships', [])
        
        if not relationships:
            story.append(Paragraph("No relationships identified.", self.styles['Normal']))
            story.append(Spacer(1, 0.3*inch))
            return story
        
        for rel in relationships:
            story.append(Paragraph(
                f"{rel.get('source', 'N/A')} → {rel.get('type', 'relates to')} → {rel.get('target', 'N/A')}",
                self.styles['Normal']
            ))
            story.append(Paragraph(
                f"Confidence: {rel.get('confidence', 0):.2f}",
                self.styles['Normal']
            ))
            story.append(Spacer(1, 0.1*inch))
        
        story.append(Spacer(1, 0.2*inch))
        return story


class TimelineSection(BaseSection):
    """Timeline section."""
    
    def build(self, data: Dict[str, Any]) -> List:
        story = []
        
        story.append(Paragraph("Timeline", self.styles['SectionHeading']))
        story.append(Spacer(1, 0.2*inch))
        
        timeline = data.get('timeline', [])
        
        if not timeline:
            story.append(Paragraph("No timeline events recorded.", self.styles['Normal']))
            story.append(Spacer(1, 0.3*inch))
            return story
        
        for event in timeline:
            story.append(Paragraph(
                f"<b>{event.get('date', 'N/A')}</b>: {event.get('title', 'Event')}",
                self.styles['Normal']
            ))
            if event.get('description'):
                story.append(Paragraph(
                    f"  {event.get('description')}",
                    self.styles['Normal']
                ))
            story.append(Spacer(1, 0.1*inch))
        
        story.append(Spacer(1, 0.2*inch))
        return story


class EvidenceSection(BaseSection):
    """Evidence appendix section."""
    
    def build(self, data: Dict[str, Any]) -> List:
        story = []
        
        story.append(Paragraph("Evidence Appendix", self.styles['SectionHeading']))
        story.append(Spacer(1, 0.2*inch))
        
        evidence = data.get('evidence', [])
        
        if not evidence:
            story.append(Paragraph("No evidence recorded.", self.styles['Normal']))
            story.append(Spacer(1, 0.3*inch))
            return story
        
        for item in evidence:
            story.append(Paragraph(
                f"<b>{item.get('id', 'N/A')}</b>",
                self.styles['SubHeading']
            ))
            story.append(Paragraph(
                f"Type: {item.get('type', 'N/A')}",
                self.styles['Normal']
            ))
            story.append(Paragraph(
                f"Source: {item.get('source', 'N/A')}",
                self.styles['Normal']
            ))
            story.append(Paragraph(
                f"Value: {item.get('value', 'N/A')}",
                self.styles['Normal']
            ))
            story.append(Spacer(1, 0.15*inch))
        
        return story


class SourcesSection(BaseSection):
    """Sources used section."""
    
    def build(self, data: Dict[str, Any]) -> List:
        story = []
        
        story.append(Paragraph("Sources Used", self.styles['SectionHeading']))
        story.append(Spacer(1, 0.2*inch))
        
        sources = data.get('sources', [])
        
        if not sources:
            story.append(Paragraph("No sources recorded.", self.styles['Normal']))
            story.append(Spacer(1, 0.3*inch))
            return story
        
        for source in sources:
            story.append(Paragraph(
                f"• {source.get('name', 'N/A')}: {source.get('description', 'N/A')}",
                self.styles['Normal']
            ))
        
        story.append(Spacer(1, 0.3*inch))
        return story


class ConfidenceSection(BaseSection):
    """Confidence summary section."""
    
    def build(self, data: Dict[str, Any]) -> List:
        story = []
        
        story.append(Paragraph("Confidence Summary", self.styles['SectionHeading']))
        story.append(Spacer(1, 0.2*inch))
        
        confidence_data = data.get('confidence_summary', {})
        
        story.append(Paragraph(
            f"Average Confidence: {confidence_data.get('average', 0):.2f}",
            self.styles['Normal']
        ))
        story.append(Paragraph(
            f"High Confidence Items: {confidence_data.get('high_count', 0)}",
            self.styles['Normal']
        ))
        story.append(Paragraph(
            f"Medium Confidence Items: {confidence_data.get('medium_count', 0)}",
            self.styles['Normal']
        ))
        story.append(Paragraph(
            f"Low Confidence Items: {confidence_data.get('low_count', 0)}",
            self.styles['Normal']
        ))
        
        story.append(Spacer(1, 0.3*inch))
        return story
