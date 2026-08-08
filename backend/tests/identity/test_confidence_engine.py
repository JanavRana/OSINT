"""
Tests for confidence engine.
"""

import pytest
from datetime import datetime, timedelta

from app.identity.confidence.engine import (
    ConfidenceEngine,
    ConfidenceWeights,
    VERIFICATION_METHOD_SCORES,
)
from app.identity.types import VerificationMethod


@pytest.fixture
def engine():
    """Provide confidence engine with default weights."""
    return ConfidenceEngine()


def test_calculate_basic_score(engine):
    """Test basic confidence score calculation."""
    score = engine.calculate_score(
        source_reliability=0.9,
        verification_method=VerificationMethod.API_CONFIRMED,
        corroboration_count=0,
        observed_at=datetime.utcnow(),
        plugin_success_rate=0.95
    )
    
    assert 0.0 <= score.value <= 1.0
    assert score.factors.source_reliability == 0.9
    assert score.factors.verification_method == VERIFICATION_METHOD_SCORES[VerificationMethod.API_CONFIRMED]


def test_corroboration_increases_confidence(engine):
    """Test that corroboration increases confidence."""
    # No corroboration
    score_0 = engine.calculate_score(
        source_reliability=0.8,
        verification_method=VerificationMethod.HTML_SCRAPE,
        corroboration_count=0,
        observed_at=datetime.utcnow(),
        plugin_success_rate=0.8
    )
    
    # With corroboration
    score_2 = engine.calculate_score(
        source_reliability=0.8,
        verification_method=VerificationMethod.HTML_SCRAPE,
        corroboration_count=2,
        observed_at=datetime.utcnow(),
        plugin_success_rate=0.8
    )
    
    assert score_2.value > score_0.value


def test_freshness_decay(engine):
    """Test that older observations have lower confidence."""
    now = datetime.utcnow()
    old = now - timedelta(days=60)
    
    # Fresh observation
    score_fresh = engine.calculate_score(
        source_reliability=0.8,
        verification_method=VerificationMethod.API_CONFIRMED,
        corroboration_count=0,
        observed_at=now,
        plugin_success_rate=0.8
    )
    
    # Old observation
    score_old = engine.calculate_score(
        source_reliability=0.8,
        verification_method=VerificationMethod.API_CONFIRMED,
        corroboration_count=0,
        observed_at=old,
        plugin_success_rate=0.8
    )
    
    assert score_fresh.factors.freshness > score_old.factors.freshness


def test_verification_method_affects_score(engine):
    """Test that different verification methods produce different scores."""
    score_api = engine.calculate_score(
        source_reliability=0.8,
        verification_method=VerificationMethod.API_CONFIRMED,
        corroboration_count=0,
        observed_at=datetime.utcnow(),
        plugin_success_rate=0.8
    )
    
    score_html = engine.calculate_score(
        source_reliability=0.8,
        verification_method=VerificationMethod.HTML_SCRAPE,
        corroboration_count=0,
        observed_at=datetime.utcnow(),
        plugin_success_rate=0.8
    )
    
    # API confirmed should have higher method score
    assert score_api.factors.verification_method > score_html.factors.verification_method


def test_recalculate_with_corroboration(engine):
    """Test recalculating confidence with new corroboration."""
    initial_score = engine.calculate_score(
        source_reliability=0.8,
        verification_method=VerificationMethod.API_CONFIRMED,
        corroboration_count=0,
        observed_at=datetime.utcnow(),
        plugin_success_rate=0.8
    )
    
    # Recalculate with corroboration
    new_score = engine.recalculate_with_corroboration(
        initial_score,
        new_corroboration_count=2
    )
    
    assert new_score.value > initial_score.value
    assert new_score.factors.corroboration > initial_score.factors.corroboration


def test_score_clamped_to_range(engine):
    """Test that scores are clamped to [0, 1]."""
    # Maximum inputs
    score_max = engine.calculate_score(
        source_reliability=1.0,
        verification_method=VerificationMethod.API_CONFIRMED,
        corroboration_count=5,
        observed_at=datetime.utcnow(),
        plugin_success_rate=1.0
    )
    
    assert score_max.value <= 1.0
    
    # Minimum inputs
    score_min = engine.calculate_score(
        source_reliability=0.0,
        verification_method=VerificationMethod.REDIRECT_INFERENCE,
        corroboration_count=0,
        observed_at=datetime.utcnow() - timedelta(days=365),
        plugin_success_rate=0.0
    )
    
    assert score_min.value >= 0.0


def test_confidence_score_to_dict(engine):
    """Test converting confidence score to dictionary."""
    score = engine.calculate_score(
        source_reliability=0.8,
        verification_method=VerificationMethod.API_CONFIRMED,
        corroboration_count=1,
        observed_at=datetime.utcnow(),
        plugin_success_rate=0.85
    )
    
    score_dict = score.to_dict()
    
    assert "value" in score_dict
    assert "breakdown" in score_dict
    assert "weights_version" in score_dict
    assert score_dict["breakdown"]["source_reliability"] == 0.8


def test_custom_weights():
    """Test confidence engine with custom weights."""
    custom_weights = ConfidenceWeights(
        w_reliability=0.5,
        w_method=0.3,
        w_corroboration=0.1,
        w_freshness=0.05,
        w_historical=0.05,
        version="2.0"
    )
    
    engine = ConfidenceEngine(weights=custom_weights)
    
    score = engine.calculate_score(
        source_reliability=0.9,
        verification_method=VerificationMethod.API_CONFIRMED,
        corroboration_count=0,
        observed_at=datetime.utcnow(),
        plugin_success_rate=0.8
    )
    
    assert score.weights_version == "2.0"
