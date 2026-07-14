"""
Tests for ReportGenerator.
"""

from app.reporting.report_generator import ReportGenerator


def test_generate_report_basic():
    """Test basic PDF generation."""
    generator = ReportGenerator()
    
    investigation_data = {
        'investigation': {
            'id': 'test-id-123',
            'name': 'Test Investigation',
            'status': 'completed',
            'created_at': '2024-01-01T00:00:00Z',
            'updated_at': '2024-01-01T01:00:00Z',
        },
        'statistics': {
            'total_connectors': 2,
            'total_facts': 5,
            'total_entities': 3,
            'total_relationships': 2,
        },
        'connectors': [],
        'entities': [],
        'relationships': [],
        'timeline': [],
        'evidence': [],
        'sources': [],
        'confidence_summary': {
            'average': 0.85,
            'high_count': 3,
            'medium_count': 1,
            'low_count': 1,
        },
    }
    
    pdf_bytes = generator.generate_report(investigation_data)
    
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0
    assert pdf_bytes[:4] == b'%PDF'


def test_generate_report_with_entities():
    """Test PDF generation with entities."""
    generator = ReportGenerator()
    
    investigation_data = {
        'investigation': {
            'id': 'test-id-456',
            'name': 'Entity Test',
            'status': 'completed',
            'created_at': '2024-01-01T00:00:00Z',
            'updated_at': '2024-01-01T01:00:00Z',
        },
        'statistics': {
            'total_connectors': 1,
            'total_facts': 3,
            'total_entities': 2,
            'total_relationships': 1,
        },
        'connectors': [
            {
                'name': 'WHOIS',
                'status': 'success',
                'started_at': '2024-01-01T00:00:00Z',
                'duration': '1.5s',
            }
        ],
        'entities': [
            {
                'type': 'Domain',
                'value': 'example.com',
                'confidence': 0.95,
                'attributes': {'registrar': 'Test Registrar'},
            },
            {
                'type': 'Email',
                'value': 'admin@example.com',
                'confidence': 0.85,
                'attributes': {},
            }
        ],
        'relationships': [
            {
                'source': 'example.com',
                'type': 'has_contact',
                'target': 'admin@example.com',
                'confidence': 0.9,
            }
        ],
        'timeline': [],
        'evidence': [],
        'sources': [],
        'confidence_summary': {
            'average': 0.9,
            'high_count': 2,
            'medium_count': 0,
            'low_count': 0,
        },
    }
    
    pdf_bytes = generator.generate_report(investigation_data)
    
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0
    assert pdf_bytes[:4] == b'%PDF'
