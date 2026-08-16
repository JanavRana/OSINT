"""
reporting/sections.py

Professional PDF section builders for INTEL WEAVE OSINT Evidence Reports.
"""

from __future__ import annotations

import base64
import io
import hashlib
import html
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


def safe_cell_text(val: Any, max_len: int = 250) -> str:
    """Safely convert, truncate, and XML-escape text for ReportLab Paragraph cells."""
    if val is None:
        return "—"
    s = str(val).strip()
    if not s:
        return "—"
    if len(s) > max_len:
        s = s[:max_len] + "…"
    # Escape XML special chars safely for ReportLab's ParaParser (which doesn't support &#x27;)
    s = (
        s.replace("&", "&amp;")
         .replace("<", "&lt;")
         .replace(">", "&gt;")
         .replace('"', "&quot;")
         .replace("'", "&#39;")
    )
    return s




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
                spaceBefore=12,
                spaceAfter=6,
            ))

        if 'SubHeading' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='SubHeading',
                fontName='Helvetica',
                fontSize=9,
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

        if 'BodyTextCustom' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='BodyTextCustom',
                fontName='Helvetica',
                fontSize=8.5,
                leading=12,
                textColor=colors.HexColor('#334155'),
                alignment=TA_LEFT,
            ))
    
    def build(self, data: Dict[str, Any]) -> List:
        """Build section content. Override in subclasses."""
        return []


class CoverPage(BaseSection):
    """
    Page 1: Full-Page Executive Summary & OSINT Investigation Dossier.
    """
    
    def build(self, data: Dict[str, Any]) -> List:
        story = []
        
        investigation = data.get('investigation', {})
        stats = data.get('statistics', {})
        connectors = data.get('connectors', [])
        facts = data.get('facts', [])
        
        case_name = safe_cell_text(investigation.get('name', 'Untitled Investigation'), 100)
        inv_id = safe_cell_text(investigation.get('id', 'N/A'), 36)
        target = safe_cell_text(investigation.get('seed_value', 'N/A'), 120)
        category_str = safe_cell_text(investigation.get('category', 'Target Identifier'), 50)
        investigator_str = safe_cell_text(investigation.get('investigator', 'Lead OSINT Investigator'), 60)
        status_str = safe_cell_text(str(investigation.get('status', 'ACTIVE')).upper(), 20)
        created_at = safe_cell_text(investigation.get('created_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S')), 30)
        
        avg_conf = stats.get('average_confidence', 0.0)
        avg_conf_pct = f"{int(round(avg_conf * 100))}%" if isinstance(avg_conf, (int, float)) else "N/A"
        
        # Hash signature for dossier validation
        raw_hash_seed = f"{inv_id}:{target}:{created_at}"
        hash_digest = hashlib.sha256(raw_hash_seed.encode('utf-8')).hexdigest()[:16].upper()
        
        # ── 1. Center-Aligned Main Header Banner ──────────────────────────────
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
        
        # ── 2. Investigation Case Metadata Table (Left-oriented content) ─────
        details_data = [
            [
                Paragraph(f"<b>Case Name:</b> {case_name}", self.styles['TableCell']),
                Paragraph(f"<b>Category:</b> <font color='#0284c7'><b>{category_str}</b></font>", self.styles['TableCell'])
            ],
            [
                Paragraph(f"<b>Investigation ID:</b> <font face='Courier'>{inv_id[:18]}..</font>", self.styles['TableCellMono']),
                Paragraph(f"<b>Status:</b> <font color='#10b981'><b>{status_str}</b></font>", self.styles['TableCell'])
            ],
            [
                Paragraph(f"<b>Target Seed:</b> <font face='Courier'>{target}</font>", self.styles['TableCellMono']),
                Paragraph(f"<b>Lead Investigator:</b> {investigator_str}", self.styles['TableCell'])
            ],
            [
                Paragraph(f"<b>Generated Date:</b> {created_at}", self.styles['TableCell']),
                Paragraph("<b>Classification:</b> TLP:AMBER · CONFIDENTIAL", self.styles['TableCell'])
            ]
        ]
        details_table = Table(details_data, colWidths=[4.3 * inch, 2.4 * inch])
        details_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('PADDING', (0, 0), (-1, -1), 6),
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
        
        # ── 4. Executive Assessment & Case Findings Summary Box ────────────────
        story.append(Paragraph("Executive Assessment & OSINT Findings", self.styles['SectionHeading']))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0'), spaceAfter=6))
        
        assessment_p1 = (
            f"This intelligence dossier documents OSINT correlation conducted for investigation "
            f"<b>{case_name}</b> targeting <b>{category_str}</b> identifier <font face='Courier'><b>{target}</b></font>. "
            f"The Intel Weave platform executed <b>{stats.get('total_connectors', 0)} OSINT connectors</b>, yielding "
            f"<b>{stats.get('total_facts', 0)} normalized facts</b> with an aggregate verification confidence of <b>{avg_conf_pct}</b>."
        )
        assessment_p2 = (
            f"Extracted intelligence encompasses technical metadata, active platform records, and historical activity timestamps. "
            f"All findings have been normalized and recorded into the persistent investigation ledger by <b>{investigator_str}</b>."
        )
        
        assessment_data = [
            [Paragraph(assessment_p1, self.styles['BodyTextCustom'])],
            [Paragraph(assessment_p2, self.styles['BodyTextCustom'])],
        ]
        assessment_table = Table(assessment_data, colWidths=[6.7 * inch])
        assessment_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
            ('PADDING', (0, 0), (-1, -1), 7),
        ]))
        story.append(assessment_table)
        story.append(Spacer(1, 0.15 * inch))
        
        # ── 5. Connector Intelligence Summary Table ───────────────────────────
        story.append(Paragraph("OSINT Connector Coverage Summary", self.styles['SectionHeading']))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0'), spaceAfter=6))
        
        cov_data = [
            [
                Paragraph("<b>Connector Name</b>", self.styles['TableHead']),
                Paragraph("<b>Execution Status</b>", self.styles['TableHead']),
                Paragraph("<b>Duration</b>", self.styles['TableHead']),
                Paragraph("<b>Timestamp</b>", self.styles['TableHead']),
            ]
        ]
        
        for c in connectors[:4]:  # Show top connectors summary on Page 1
            st_str = safe_cell_text(c.get('status', 'N/A'), 20).upper()
            st_color = "#10b981" if st_str == "SUCCESS" else "#ef4444" if st_str == "FAILED" else "#f59e0b"
            name_str = safe_cell_text(c.get('name', 'N/A'), 50)
            dur_str = safe_cell_text(c.get('duration', 'N/A'), 20)
            start_str = safe_cell_text(c.get('started_at', 'N/A'), 20)
            cov_data.append([
                Paragraph(f"<b>{name_str}</b>", self.styles['TableCell']),
                Paragraph(f"<font color='{st_color}'><b>{st_str}</b></font>", self.styles['TableCell']),
                Paragraph(dur_str, self.styles['TableCell']),
                Paragraph(start_str, self.styles['TableCellMono']),
            ])
            
        if len(connectors) == 0:
            cov_data.append([
                Paragraph("Automated connector execution recorded.", self.styles['TableCell']),
                Paragraph("READY", self.styles['TableCell']),
                Paragraph("< 1.0s", self.styles['TableCell']),
                Paragraph("N/A", self.styles['TableCellMono']),
            ])

        cov_table = Table(cov_data, colWidths=[2.2 * inch, 1.5 * inch, 1.3 * inch, 1.7 * inch])
        cov_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f172a')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
            ('PADDING', (0, 0), (-1, -1), 4.5),
        ]))
        story.append(cov_table)
        story.append(Spacer(1, 0.15 * inch))
        
        # ── 6. Investigator Attestation & Verification Footer Card ─────────────
        sign_data = [
            [
                Paragraph(f"<b>Investigator Signature:</b> ___________________________", self.styles['TableCell']),
                Paragraph(f"<b>Verification Hash:</b> <font face='Courier'>SHA256-{hash_digest}</font>", self.styles['TableCellMono'])
            ]
        ]
        sign_table = Table(sign_data, colWidths=[4.2 * inch, 2.5 * inch])
        sign_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f1f5f9')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e1')),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(sign_table)
        
        story.append(PageBreak())
        return story


class IdentifiersSection(BaseSection):
    """
    Extracted Identifiers & Evidence Table (Left-oriented table, flows naturally).
    """
    
    def build(self, data: Dict[str, Any]) -> List:
        story = []
        
        story.append(Paragraph("Extracted Identifiers & Evidence", self.styles['SectionHeading']))
        story.append(Paragraph("Inventory of normalized facts extracted across active connectors.", self.styles['SubHeading']))
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
            
            fact_type = safe_cell_text(str(f.get('type', 'generic')).replace('_', ' ').title(), 50)
            val_str = safe_cell_text(f.get('value'), 200)
            source_str = safe_cell_text(f.get('connector', 'OSINT'), 40)
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
        return story


class ConnectorSection(BaseSection):
    """
    Connector Execution Summary Log (Left-oriented table, flows naturally).
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
            status_str = safe_cell_text(c.get('status', 'N/A'), 20).upper()
            status_color = "#10b981" if status_str == "SUCCESS" else "#ef4444" if status_str == "FAILED" else "#f59e0b"
            name_str = safe_cell_text(c.get('name', 'N/A'), 50)
            start_str = safe_cell_text(c.get('started_at', 'N/A'), 20)
            dur_str = safe_cell_text(c.get('duration', 'N/A'), 20)
            err_str = safe_cell_text(c.get('error') or 'None', 150)
            
            table_data.append([
                Paragraph(f"<b>{name_str}</b>", self.styles['TableCell']),
                Paragraph(f"<font color='{status_color}'><b>{status_str}</b></font>", self.styles['TableCell']),
                Paragraph(start_str, self.styles['TableCell']),
                Paragraph(dur_str, self.styles['TableCell']),
                Paragraph(err_str, self.styles['TableCell']),
            ])
            
        c_table = Table(table_data, colWidths=[1.3 * inch, 1.0 * inch, 1.2 * inch, 1.0 * inch, 2.2 * inch])
        c_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f172a')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
            ('PADDING', (0, 0), (-1, -1), 4.5),
        ]))
        
        story.append(c_table)
        story.append(Spacer(1, 0.2 * inch))
        return story


class TimelineSection(BaseSection):
    """
    Chronological Event Timeline (Left-oriented table, flows naturally).
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
            date_str = safe_cell_text(t.get('date', 'N/A'), 30)
            title_str = safe_cell_text(t.get('title', 'Event'), 80)
            conn_str = safe_cell_text(t.get('connector', 'OSINT'), 40)
            desc_str = safe_cell_text(t.get('description') or '—', 150)

            table_data.append([
                Paragraph(date_str, self.styles['TableCellMono']),
                Paragraph(f"<b>{title_str}</b>", self.styles['TableCell']),
                Paragraph(conn_str, self.styles['TableCell']),
                Paragraph(desc_str, self.styles['TableCell']),
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
