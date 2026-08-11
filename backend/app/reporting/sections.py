"""
reporting/sections.py

Professional PDF section builders for INTEL WEAVE OSINT Evidence Reports.
"""

from __future__ import annotations

import base64
import io
import math
from datetime import datetime
from typing import Any, Dict, List

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Image,
    PageBreak,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.graphics.shapes import Drawing, Rect, Circle, String, Line


class BaseSection:
    """Base class for report sections."""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles for report formatting."""
        if 'ReportHeaderCenter' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='ReportHeaderCenter',
                fontName='Helvetica-Bold',
                fontSize=18,
                leading=22,
                textColor=colors.HexColor('#ffffff'),
                alignment=TA_CENTER,
            ))
            
        if 'SectionHeading' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='SectionHeading',
                fontName='Helvetica-Bold',
                fontSize=13,
                leading=16,
                textColor=colors.HexColor('#0f172a'),
                spaceBefore=14,
                spaceAfter=8,
            ))

        if 'SubHeading' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='SubHeading',
                fontName='Helvetica',
                fontSize=9.5,
                leading=12,
                textColor=colors.HexColor('#64748b'),
                spaceAfter=6,
            ))

        if 'CardLabel' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='CardLabel',
                fontName='Helvetica-Bold',
                fontSize=8,
                leading=10,
                textColor=colors.HexColor('#64748b'),
                alignment=TA_CENTER,
            ))

        if 'CardValue' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='CardValue',
                fontName='Helvetica-Bold',
                fontSize=13,
                leading=15,
                textColor=colors.HexColor('#0f172a'),
                alignment=TA_CENTER,
            ))

        if 'TableHead' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='TableHead',
                fontName='Helvetica-Bold',
                fontSize=8.5,
                leading=10,
                textColor=colors.HexColor('#ffffff'),
                alignment=TA_LEFT,
            ))

        if 'TableCell' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='TableCell',
                fontName='Helvetica',
                fontSize=8,
                leading=10,
                textColor=colors.HexColor('#334155'),
                alignment=TA_LEFT,
            ))

        if 'TableCellMono' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='TableCellMono',
                fontName='Courier',
                fontSize=7.5,
                leading=9,
                textColor=colors.HexColor('#0f172a'),
                alignment=TA_LEFT,
            ))
    
    def build(self, data: Dict[str, Any]) -> List:
        """Build section content. Override in subclasses."""
        return []


class CoverPage(BaseSection):
    """
    Page 1: Executive Summary Card + Centered Dynamic Relationship Graph.
    """
    
    def build(self, data: Dict[str, Any]) -> List:
        story = []
        
        investigation = data.get('investigation', {})
        stats = data.get('statistics', {})
        facts = data.get('facts', [])
        
        case_name = investigation.get('name', 'Untitled Investigation')
        target = investigation.get('seed_value', 'N/A')
        seed_type = str(investigation.get('seed_type', 'N/A')).upper()
        status_str = str(investigation.get('status', 'ACTIVE')).upper()
        created_at = investigation.get('created_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        avg_conf = stats.get('average_confidence', 0.0)
        avg_conf_pct = f"{int(round(avg_conf * 100))}%" if isinstance(avg_conf, (int, float)) else "N/A"
        
        # ── 1. Center-Aligned Header Banner (INTEL WEAVE EVIDENCE REPORT) ──────
        banner_content = [
            [
                Paragraph("<b>INTEL WEAVE EVIDENCE REPORT</b>", self.styles['ReportHeaderCenter'])
            ]
        ]
        banner_table = Table(banner_content, colWidths=[6.7 * inch])
        banner_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#0f172a')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 10),
        ]))
        story.append(banner_table)
        story.append(Spacer(1, 0.15 * inch))
        
        # ── 2. Investigation Details Card ─────────────────────────────────────
        details_data = [
            [
                Paragraph(f"<b>Case Name:</b> {case_name}", self.styles['TableCell']),
                Paragraph(f"<b>Status:</b> <font color='#0284c7'><b>{status_str}</b></font>", self.styles['TableCell'])
            ],
            [
                Paragraph(f"<b>Target Seed:</b> <font face='Courier'>{target}</font> ({seed_type})", self.styles['TableCell']),
                Paragraph(f"<b>Created:</b> {created_at}", self.styles['TableCell'])
            ]
        ]
        details_table = Table(details_data, colWidths=[4.5 * inch, 2.2 * inch])
        details_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e1')),
            ('PADDING', (0, 0), (-1, -1), 7),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(details_table)
        story.append(Spacer(1, 0.15 * inch))
        
        # ── 3. Executive Metrics Grid ──────────────────────────────────────────
        metric_cards = [
            [
                Paragraph("DISCOVERED IDENTIFIERS", self.styles['CardLabel']),
                Paragraph("EXECUTED CONNECTORS", self.styles['CardLabel']),
                Paragraph("AVG CONFIDENCE SCORE", self.styles['CardLabel']),
                Paragraph("TOTAL FACTS", self.styles['CardLabel'])
            ],
            [
                Paragraph(str(stats.get('total_facts', 0)), self.styles['CardValue']),
                Paragraph(f"{stats.get('successful_connectors', 0)} / {stats.get('total_connectors', 0)}", self.styles['CardValue']),
                Paragraph(avg_conf_pct, self.styles['CardValue']),
                Paragraph(str(stats.get('total_facts', 0)), self.styles['CardValue'])
            ]
        ]
        metrics_table = Table(metric_cards, colWidths=[1.675 * inch, 1.675 * inch, 1.675 * inch, 1.675 * inch])
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f1f5f9')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(metrics_table)
        story.append(Spacer(1, 0.15 * inch))
        
        # ── 4. Centered Dynamic Relationship Graph Section ────────────────────
        story.append(Paragraph("Relationship Graph Visualization", self.styles['SectionHeading']))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0'), spaceAfter=8))
        
        graph_b64 = data.get('graph_image_base64')
        if graph_b64 and isinstance(graph_b64, str):
            try:
                if graph_b64.startswith("data:image"):
                    graph_b64 = graph_b64.split(",", 1)[1]
                img_data = base64.b64decode(graph_b64)
                img_stream = io.BytesIO(img_data)
                img_flowable = Image(img_stream, width=6.5 * inch, height=3.2 * inch)
                
                # Wrap in centered container table
                center_table = Table([[img_flowable]], colWidths=[6.7 * inch])
                center_table.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER')]))
                story.append(center_table)
            except Exception:
                story.append(self._build_dynamic_vector_graph(target, facts))
        else:
            story.append(self._build_dynamic_vector_graph(target, facts))
            
        story.append(PageBreak())
        return story

    def _build_dynamic_vector_graph(self, target: str, facts: List[Dict[str, Any]]) -> Table:
        """Dynamically build a centered vector graph tailored to this specific investigation's facts."""
        width = 460
        height = 220
        d = Drawing(width, height)
        d.add(Rect(0, 0, width, height, fillColor=colors.HexColor("#0f172a"), rx=8, ry=8))
        
        cx, cy = 230, 110
        # Center Seed Node
        d.add(Circle(cx, cy, 28, fillColor=colors.HexColor("#0284c7"), strokeColor=colors.HexColor("#38bdf8"), strokeWidth=2))
        d.add(String(cx, cy - 3, "TARGET SEED", fontName="Helvetica-Bold", fontSize=6.5, fillColor=colors.white, textAnchor="middle"))
        
        # Pick top unique fact items for dynamic node placement
        fact_nodes = []
        palette = ["#10b981", "#f59e0b", "#6366f1", "#ec4899", "#14b8a6", "#8b5cf6"]
        
        for idx, f in enumerate(facts[:6]):
            f_type = str(f.get('type', 'FACT')).replace('_', ' ').upper()
            f_val = str(f.get('value', ''))
            label = f_type if len(f_type) <= 12 else f_type[:10] + '..'
            fact_nodes.append((label, f_val, palette[idx % len(palette)]))
            
        if not fact_nodes:
            fact_nodes = [
                ("IDENTIFIER", "Seed Address", "#10b981"),
                ("CONNECTORS", "Active Execution", "#f59e0b"),
            ]

        num_nodes = len(fact_nodes)
        radius = 85
        
        for i, (label, val, color) in enumerate(fact_nodes):
            angle = (2 * math.pi / num_nodes) * i
            nx = cx + radius * math.cos(angle)
            ny = cy + radius * math.sin(angle)
            
            d.add(Line(cx, cy, nx, ny, strokeColor=colors.HexColor("#334155"), strokeWidth=1.5))
            d.add(Circle(nx, ny, 20, fillColor=colors.HexColor(color), strokeColor=colors.white, strokeWidth=1.5))
            d.add(String(nx, ny - 3, label[:10], fontName="Helvetica-Bold", fontSize=5.5, fillColor=colors.white, textAnchor="middle"))

        d.add(String(cx, 12, f"Target: {target[:32]}", fontName="Courier", fontSize=7.5, fillColor=colors.HexColor("#94a3b8"), textAnchor="middle"))
        
        # Center in Table container
        wrapper = Table([[d]], colWidths=[6.7 * inch])
        wrapper.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER')]))
        return wrapper


class IdentifiersSection(BaseSection):
    """
    Extracted Identifiers & Evidence Table (Flows naturally on continuous pages).
    """
    
    def build(self, data: Dict[str, Any]) -> List:
        story = []
        
        story.append(Paragraph("Extracted Identifiers & Data", self.styles['SectionHeading']))
        story.append(Paragraph("Comprehensive inventory of normalized intelligence facts.", self.styles['SubHeading']))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0'), spaceAfter=8))
        
        facts = data.get('facts', [])
        if not facts:
            story.append(Paragraph("No identifiers discovered for this investigation.", self.styles['TableCell']))
            story.append(Spacer(1, 0.15 * inch))
            return story
        
        table_data = [
            [
                Paragraph("<b>Type / Platform</b>", self.styles['TableHead']),
                Paragraph("<b>Extracted Value</b>", self.styles['TableHead']),
                Paragraph("<b>Confidence</b>", self.styles['TableHead']),
                Paragraph("<b>Source</b>", self.styles['TableHead']),
                Paragraph("<b>Reference</b>", self.styles['TableHead']),
            ]
        ]
        
        for f in facts:
            conf_val = f.get('confidence', 1.0)
            conf_pct = f"{int(round(conf_val * 100))}%"
            
            fact_type = str(f.get('type', 'generic')).replace('_', ' ').title()
            val_str = str(f.get('value', ''))
            source_str = str(f.get('connector', 'OSINT'))
            meta = f.get('metadata', {})
            
            profile_url = meta.get('profile_url') or meta.get('wallet_address')
            ref_cell = f"<font color='#0284c7'><u>{source_str}</u></font>" if profile_url else "—"
            
            table_data.append([
                Paragraph(fact_type, self.styles['TableCell']),
                Paragraph(val_str, self.styles['TableCellMono']),
                Paragraph(conf_pct, self.styles['TableCell']),
                Paragraph(source_str, self.styles['TableCell']),
                Paragraph(ref_cell, self.styles['TableCell']),
            ])
            
        id_table = Table(table_data, colWidths=[1.5 * inch, 2.7 * inch, 0.8 * inch, 0.8 * inch, 0.9 * inch])
        id_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f172a')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        
        story.append(id_table)
        story.append(Spacer(1, 0.2 * inch))
        # No PageBreak here - continuous flow!
        return story


class ConnectorSection(BaseSection):
    """
    Connector Execution Summary Log (Flows naturally on continuous pages).
    """
    
    def build(self, data: Dict[str, Any]) -> List:
        story = []
        
        story.append(Paragraph("Connector Execution Log", self.styles['SectionHeading']))
        story.append(Paragraph("Execution summary across registered OSINT connector plugins.", self.styles['SubHeading']))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0'), spaceAfter=8))
        
        connectors = data.get('connectors', [])
        if not connectors:
            story.append(Paragraph("No connectors executed.", self.styles['TableCell']))
            story.append(Spacer(1, 0.15 * inch))
            return story
        
        table_data = [
            [
                Paragraph("<b>Connector</b>", self.styles['TableHead']),
                Paragraph("<b>Status</b>", self.styles['TableHead']),
                Paragraph("<b>Started At</b>", self.styles['TableHead']),
                Paragraph("<b>Duration</b>", self.styles['TableHead']),
                Paragraph("<b>Error Details</b>", self.styles['TableHead']),
            ]
        ]
        
        for c in connectors:
            status_str = str(c.get('status', 'N/A')).upper()
            status_color = "#10b981" if status_str == "SUCCESS" else "#ef4444" if status_str == "FAILED" else "#f59e0b"
            
            table_data.append([
                Paragraph(f"<b>{c.get('name', 'N/A')}</b>", self.styles['TableCell']),
                Paragraph(f"<font color='{status_color}'><b>{status_str}</b></font>", self.styles['TableCell']),
                Paragraph(str(c.get('started_at', 'N/A')), self.styles['TableCell']),
                Paragraph(str(c.get('duration', 'N/A')), self.styles['TableCell']),
                Paragraph(str(c.get('error') or 'None'), self.styles['TableCell']),
            ])
            
        c_table = Table(table_data, colWidths=[1.3 * inch, 1.0 * inch, 1.2 * inch, 1.0 * inch, 2.2 * inch])
        c_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f172a')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
            ('PADDING', (0, 0), (-1, -1), 5),
        ]))
        
        story.append(c_table)
        story.append(Spacer(1, 0.2 * inch))
        # No PageBreak here - continuous flow!
        return story


class TimelineSection(BaseSection):
    """
    Chronological Event Timeline (Flows naturally on continuous pages).
    """
    
    def build(self, data: Dict[str, Any]) -> List:
        story = []
        
        story.append(Paragraph("Chronological Event Timeline", self.styles['SectionHeading']))
        story.append(Paragraph("Temporal activity events extracted from normalized facts.", self.styles['SubHeading']))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0'), spaceAfter=8))
        
        timeline = data.get('timeline', [])
        if not timeline:
            story.append(Paragraph("No timeline events recorded.", self.styles['TableCell']))
            story.append(Spacer(1, 0.15 * inch))
            return story
        
        table_data = [
            [
                Paragraph("<b>Date / Time</b>", self.styles['TableHead']),
                Paragraph("<b>Event Title</b>", self.styles['TableHead']),
                Paragraph("<b>Source</b>", self.styles['TableHead']),
                Paragraph("<b>Description</b>", self.styles['TableHead']),
            ]
        ]
        
        for t in timeline[:30]:  # Limit to recent 30 events for readability
            table_data.append([
                Paragraph(str(t.get('date', 'N/A')), self.styles['TableCellMono']),
                Paragraph(f"<b>{t.get('title', 'Event')}</b>", self.styles['TableCell']),
                Paragraph(str(t.get('connector', 'OSINT')), self.styles['TableCell']),
                Paragraph(str(t.get('description') or '—'), self.styles['TableCell']),
            ])
            
        t_table = Table(table_data, colWidths=[1.4 * inch, 2.0 * inch, 1.0 * inch, 2.3 * inch])
        t_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f172a')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        
        story.append(t_table)
        story.append(Spacer(1, 0.2 * inch))
        return story


# Export compatibility aliases
ExecutiveSummary = CoverPage
InvestigationMetadata = CoverPage
UnifiedEntitiesSection = IdentifiersSection
RelationshipSection = CoverPage
EvidenceSection = IdentifiersSection
SourcesSection = ConnectorSection
ConfidenceSection = CoverPage
