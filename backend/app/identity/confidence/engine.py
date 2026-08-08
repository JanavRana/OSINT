"""
Confidence scoring engine.

Calculates confidence scores based on multiple weighted factors:
- Source reliability
- Verification method
- Corroboration
- Freshness
- Historical success
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from ..types import VerificationMethod

logger = logging.getLogger(__name__)


@dataclass
class ConfidenceFactors:
    """Individual factors contributing to confidence score."""
    source_reliability: float
    verification_method: float
    corroboration: float
    freshness: float
    historical_success: float


@dataclass
class ConfidenceScore:
    """Complete confidence score with breakdown."""
    value: float  # Final score [0, 1]
    factors: ConfidenceFactors
    weights_version: str = "1.0"
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "value": self.value,
            "breakdown": {
                "source_reliability": self.factors.source_reliability,
                "verification_method": self.factors.verification_method,
                "corroboration": self.factors.corroboration,
                "freshness": self.factors.freshness,
                "historical_success": self.factors.historical_success,
            },
            "weights_version": self.weights_version,
        }


class ConfidenceWeights:
    """
    Configurable weights for confidence factors.
    
    In production, loaded from config/identity/confidence_weights.yaml
    """
    
    def __init__(
        self,
        w_reliability: float = 0.3,
        w_method: float = 0.25,
        w_corroboration: float = 0.25,
        w_freshness: float = 0.1,
        w_historical: float = 0.1,
        version: str = "1.0"
    ):
        """
        Initialize weights.
        
        Args:
            w_reliability: Weight for source reliability
            w_method: Weight for verification method
            w_corroboration: Weight for corroboration
            w_freshness: Weight for freshness
            w_historical: Weight for historical success
            version: Version identifier for these weights
        """
        self.w_reliability = w_reliability
        self.w_method = w_method
        self.w_corroboration = w_corroboration
        self.w_freshness = w_freshness
        self.w_historical = w_historical
        self.version = version
        
        # Validate weights sum to 1.0
        total = (
            w_reliability + w_method + w_corroboration +
            w_freshness + w_historical
        )
        if abs(total - 1.0) > 0.01:
            logger.warning(
                f"Confidence weights sum to {total}, not 1.0. "
                "Scores may not be properly normalized."
            )


# Verification method score lookup table
VERIFICATION_METHOD_SCORES = {
    VerificationMethod.API_CONFIRMED: 0.95,
    VerificationMethod.GRAPHQL_CONFIRMED: 0.92,
    VerificationMethod.HTML_SCRAPE: 0.65,
    VerificationMethod.REDIRECT_INFERENCE: 0.55,
    VerificationMethod.DNS_LOOKUP: 0.85,
    VerificationMethod.SMTP_VERIFICATION: 0.80,
    VerificationMethod.CARRIER_LOOKUP: 0.90,
    VerificationMethod.PRESENCE_CHECK: 0.75,
}


class ConfidenceEngine:
    """
    Calculates confidence scores for facts.
    """
    
    def __init__(self, weights: Optional[ConfidenceWeights] = None):
        """
        Initialize confidence engine.
        
        Args:
            weights: Confidence weights configuration
        """
        self.weights = weights or ConfidenceWeights()
    
    def calculate_score(
        self,
        source_reliability: float,
        verification_method: VerificationMethod,
        corroboration_count: int = 0,
        observed_at: Optional[datetime] = None,
        plugin_success_rate: Optional[float] = None,
    ) -> ConfidenceScore:
        """
        Calculate confidence score for a fact.
        
        Args:
            source_reliability: Base reliability from platform definition [0, 1]
            verification_method: Method used for verification
            corroboration_count: Number of corroborating facts
            observed_at: When the fact was observed
            plugin_success_rate: Historical success rate for plugin [0, 1]
            
        Returns:
            ConfidenceScore with final value and breakdown
        """
        # Factor 1: Source reliability (from platform definition)
        reliability_score = source_reliability
        
        # Factor 2: Verification method score
        method_score = VERIFICATION_METHOD_SCORES.get(
            verification_method,
            0.5  # Default for unknown methods
        )
        
        # Factor 3: Corroboration score
        # More corroboration -> higher confidence
        # Diminishing returns: 1 corroboration = +0.3, 2 = +0.5, 3+ = +0.7
        if corroboration_count == 0:
            corroboration_score = 0.5  # Single-source baseline
        elif corroboration_count == 1:
            corroboration_score = 0.8
        elif corroboration_count == 2:
            corroboration_score = 0.95
        else:
            corroboration_score = 1.0
        
        # Factor 4: Freshness score
        # Decay based on age (simplified - in production would be fact-type specific)
        if observed_at:
            age_hours = (datetime.utcnow() - observed_at).total_seconds() / 3600
            if age_hours < 24:
                freshness_score = 1.0
            elif age_hours < 168:  # 1 week
                freshness_score = 0.9
            elif age_hours < 720:  # 30 days
                freshness_score = 0.7
            else:
                freshness_score = 0.5
        else:
            freshness_score = 1.0  # Assume fresh if unknown
        
        # Factor 5: Historical success score
        if plugin_success_rate is not None:
            historical_score = plugin_success_rate
        else:
            historical_score = 0.8  # Default assumption
        
        # Calculate weighted sum
        factors = ConfidenceFactors(
            source_reliability=reliability_score,
            verification_method=method_score,
            corroboration=corroboration_score,
            freshness=freshness_score,
            historical_success=historical_score,
        )
        
        final_score = (
            self.weights.w_reliability * reliability_score +
            self.weights.w_method * method_score +
            self.weights.w_corroboration * corroboration_score +
            self.weights.w_freshness * freshness_score +
            self.weights.w_historical * historical_score
        )
        
        # Clamp to [0, 1]
        final_score = max(0.0, min(1.0, final_score))
        
        logger.debug(
            f"Calculated confidence: {final_score:.3f} "
            f"(reliability={reliability_score:.2f}, method={method_score:.2f}, "
            f"corroboration={corroboration_score:.2f}, freshness={freshness_score:.2f}, "
            f"historical={historical_score:.2f})"
        )
        
        return ConfidenceScore(
            value=final_score,
            factors=factors,
            weights_version=self.weights.version,
        )
    
    def recalculate_with_corroboration(
        self,
        existing_score: ConfidenceScore,
        new_corroboration_count: int
    ) -> ConfidenceScore:
        """
        Recalculate confidence with updated corroboration.
        
        Args:
            existing_score: Existing confidence score
            new_corroboration_count: Updated corroboration count
            
        Returns:
            New ConfidenceScore
        """
        # Update corroboration factor
        if new_corroboration_count == 0:
            corroboration_score = 0.5
        elif new_corroboration_count == 1:
            corroboration_score = 0.8
        elif new_corroboration_count == 2:
            corroboration_score = 0.95
        else:
            corroboration_score = 1.0
        
        # Recalculate with new corroboration
        factors = ConfidenceFactors(
            source_reliability=existing_score.factors.source_reliability,
            verification_method=existing_score.factors.verification_method,
            corroboration=corroboration_score,
            freshness=existing_score.factors.freshness,
            historical_success=existing_score.factors.historical_success,
        )
        
        final_score = (
            self.weights.w_reliability * factors.source_reliability +
            self.weights.w_method * factors.verification_method +
            self.weights.w_corroboration * factors.corroboration +
            self.weights.w_freshness * factors.freshness +
            self.weights.w_historical * factors.historical_success
        )
        
        final_score = max(0.0, min(1.0, final_score))
        
        logger.debug(
            f"Recalculated confidence with corroboration: "
            f"{existing_score.value:.3f} -> {final_score:.3f}"
        )
        
        return ConfidenceScore(
            value=final_score,
            factors=factors,
            weights_version=self.weights.version,
        )
