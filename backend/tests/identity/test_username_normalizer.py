"""
Tests for username result normalization.
"""

import pytest
from datetime import datetime
from uuid import uuid4

from app.identity.plugin_base import DetectionOutcome, RawResult
from app.identity.types import IdentifierType
from app.identity.username.normalizer import (
    normalize_username_result,
    batch_normalize_username_results,
)


class TestUsernameNormalizer:
    """Test normalization of username detection results."""
    
    def test_normalize_successful_detection(self):
        """Test normalizing a successful username detection."""
        investigation_id = uuid4()
        
        outcome = DetectionOutcome(
            exists=True,
            http_status=200,
            evidence_fields={
                "display_name": "John Doe",
                "avatar_url": "https://example.com/avatar.jpg",
                "bio": "Software developer"
            },
            raw_snapshot_ref="snapshot_123",
            strategy_confidence_hint=0.9
        )
        
        raw_result = RawResult(
            plugin_id="github",
            identifier_type=IdentifierType.USERNAME,
            identifier_value="johndoe",
            success=True,
            timestamp=datetime.utcnow(),
            payload=outcome,
            duration_ms=250.0,
            http_status=200,
            raw_snapshot_ref="snapshot_123"
        )
        
        fact = normalize_username_result(raw_result, investigation_id)
        
        assert fact is not None
        assert fact.investigation_id == investigation_id
        assert fact.identifier_type == IdentifierType.USERNAME
        assert fact.identifier_value == "johndoe"
        assert fact.fact_type == "platform_account_found"
        assert fact.fact_payload["platform"] == "github"
        assert fact.fact_payload["exists"] is True
        assert fact.fact_payload["evidence_fields"] == outcome.evidence_fields
        assert fact.confidence.value > 0.0
    
    def test_normalize_not_found_detection(self):
        """Test normalizing a not-found detection."""
        investigation_id = uuid4()
        
        outcome = DetectionOutcome(
            exists=False,
            http_status=404,
            strategy_confidence_hint=0.9
        )
        
        raw_result = RawResult(
            plugin_id="github",
            identifier_type=IdentifierType.USERNAME,
            identifier_value="nonexistent_user_12345",
            success=True,
            timestamp=datetime.utcnow(),
            payload=outcome,
            duration_ms=150.0,
            http_status=404
        )
        
        fact = normalize_username_result(raw_result, investigation_id)
        
        assert fact is not None
        assert fact.fact_type == "platform_account_not_found"
        assert fact.fact_payload["exists"] is False
        # High confidence for explicit 404
        assert fact.confidence.value >= 0.8
    
    def test_normalize_unknown_detection(self):
        """Test normalizing an unknown detection."""
        investigation_id = uuid4()
        
        outcome = DetectionOutcome(
            exists="unknown",
            http_status=500,
            strategy_confidence_hint=0.3
        )
        
        raw_result = RawResult(
            plugin_id="someplatform",
            identifier_type=IdentifierType.USERNAME,
            identifier_value="testuser",
            success=True,
            timestamp=datetime.utcnow(),
            payload=outcome,
            duration_ms=5000.0,
            http_status=500
        )
        
        fact = normalize_username_result(raw_result, investigation_id)
        
        assert fact is not None
        assert fact.fact_type == "platform_account_unknown"
        assert fact.fact_payload["exists"] == "unknown"
        # Lower confidence for unknown results
        assert fact.confidence.value < 0.7
    
    def test_skip_failed_results(self):
        """Test that failed results are not normalized."""
        investigation_id = uuid4()
        
        raw_result = RawResult(
            plugin_id="github",
            identifier_type=IdentifierType.USERNAME,
            identifier_value="testuser",
            success=False,
            timestamp=datetime.utcnow(),
            payload={},
            error="Connection timeout"
        )
        
        fact = normalize_username_result(raw_result, investigation_id)
        
        # Should return None for failed results
        assert fact is None
    
    def test_confidence_factors(self):
        """Test that confidence breakdown includes all factors."""
        investigation_id = uuid4()
        
        outcome = DetectionOutcome(
            exists=True,
            http_status=200,
            evidence_fields={"display_name": "Test User"},
            strategy_confidence_hint=0.95
        )
        
        raw_result = RawResult(
            plugin_id="github",
            identifier_type=IdentifierType.USERNAME,
            identifier_value="testuser",
            success=True,
            timestamp=datetime.utcnow(),
            payload=outcome
        )
        
        fact = normalize_username_result(raw_result, investigation_id)
        
        assert fact is not None
        assert hasattr(fact.confidence, 'factors')
        factors = fact.confidence.factors
        
        # Check all factors are present
        assert hasattr(factors, 'source_reliability')
        assert hasattr(factors, 'verification_method')
        assert hasattr(factors, 'corroboration')
        assert hasattr(factors, 'freshness')
        assert hasattr(factors, 'historical_success')
        
        # All factors should be in [0, 1] range
        assert 0.0 <= factors.source_reliability <= 1.0
        assert 0.0 <= factors.verification_method <= 1.0
        assert 0.0 <= factors.corroboration <= 1.0
        assert 0.0 <= factors.freshness <= 1.0
        assert 0.0 <= factors.historical_success <= 1.0
    
    def test_evidence_fields_bonus(self):
        """Test that evidence fields increase confidence."""
        investigation_id = uuid4()
        
        # Result with no evidence fields
        outcome_no_evidence = DetectionOutcome(
            exists=True,
            http_status=200,
            strategy_confidence_hint=0.8
        )
        
        raw_no_evidence = RawResult(
            plugin_id="platform1",
            identifier_type=IdentifierType.USERNAME,
            identifier_value="user1",
            success=True,
            timestamp=datetime.utcnow(),
            payload=outcome_no_evidence
        )
        
        # Result with multiple evidence fields
        outcome_with_evidence = DetectionOutcome(
            exists=True,
            http_status=200,
            evidence_fields={
                "display_name": "User One",
                "avatar_url": "https://example.com/avatar.jpg",
                "bio": "Test bio",
                "location": "Test City"
            },
            strategy_confidence_hint=0.8
        )
        
        raw_with_evidence = RawResult(
            plugin_id="platform1",
            identifier_type=IdentifierType.USERNAME,
            identifier_value="user1",
            success=True,
            timestamp=datetime.utcnow(),
            payload=outcome_with_evidence
        )
        
        fact_no_evidence = normalize_username_result(raw_no_evidence, investigation_id)
        fact_with_evidence = normalize_username_result(raw_with_evidence, investigation_id)
        
        # Evidence fields should increase corroboration factor
        assert fact_with_evidence.confidence.factors.corroboration > \
               fact_no_evidence.confidence.factors.corroboration
    
    def test_batch_normalization(self):
        """Test batch normalization of multiple results."""
        investigation_id = uuid4()
        
        raw_results = []
        for i, platform in enumerate(["github", "gitlab", "reddit"]):
            outcome = DetectionOutcome(
                exists=True if i < 2 else False,
                http_status=200 if i < 2 else 404,
                strategy_confidence_hint=0.9
            )
            
            raw_result = RawResult(
                plugin_id=platform,
                identifier_type=IdentifierType.USERNAME,
                identifier_value="testuser",
                success=True,
                timestamp=datetime.utcnow(),
                payload=outcome
            )
            raw_results.append(raw_result)
        
        facts = batch_normalize_username_results(raw_results, investigation_id)
        
        assert len(facts) == 3
        assert all(f.investigation_id == investigation_id for f in facts)
        assert all(f.identifier_value == "testuser" for f in facts)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
