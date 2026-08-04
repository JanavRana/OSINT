"""
Risk scoring engine for investigations.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any
from uuid import UUID

from ..correlation.types import CorrelatedEntities, CorrelatedEntity

logger = logging.getLogger(__name__)


class RiskScorer:
    """
    Calculate risk scores for investigations based on entity patterns.
    """
    
    def calculate_investigation_risk(
        self,
        investigation_id: UUID,
        entities: CorrelatedEntities
    ) -> Dict[str, Any]:
        """
        Calculate overall risk score and indicators for an investigation.
        
        Returns:
            {
                "investigation_id": UUID,
                "overall_score": float (0-100),
                "risk_level": str ("low", "medium", "high", "critical"),
                "indicators": List[Dict],
                "factors": Dict[str, float]
            }
        """
        factors = {}
        indicators = []
        
        # Low confidence entities
        low_confidence_score = self._score_low_confidence(entities.entities)
        factors["low_confidence_entities"] = low_confidence_score
        if low_confidence_score > 0.3:
            indicators.append({
                "type": "low_confidence",
                "severity": "medium",
                "message": "Multiple entities with low confidence scores detected"
            })
        
        # Recent registrations
        recent_reg_score = self._score_recent_registrations(entities.entities)
        factors["recent_registrations"] = recent_reg_score
        if recent_reg_score > 0.5:
            indicators.append({
                "type": "recent_registration",
                "severity": "high",
                "message": "Recently registered domains detected"
            })
        
        # Privacy protection
        privacy_score = self._score_privacy_protection(entities.entities)
        factors["privacy_protection"] = privacy_score
        if privacy_score > 0.4:
            indicators.append({
                "type": "privacy_protection",
                "severity": "medium",
                "message": "Domain(s) using privacy protection services"
            })
        
        # Shared infrastructure
        shared_infra_score = self._score_shared_infrastructure(entities)
        factors["shared_infrastructure"] = shared_infra_score
        if shared_infra_score > 0.6:
            indicators.append({
                "type": "shared_infrastructure",
                "severity": "high",
                "message": "Multiple domains sharing registrar/nameservers"
            })
        
        # Entity concentration
        concentration_score = self._score_entity_concentration(entities)
        factors["entity_concentration"] = concentration_score
        if concentration_score > 0.7:
            indicators.append({
                "type": "entity_concentration",
                "severity": "medium",
                "message": "High concentration of related entities detected"
            })
        
        # Calculate weighted overall score (0-100)
        overall_score = (
            low_confidence_score * 15 +
            recent_reg_score * 30 +
            privacy_score * 20 +
            shared_infra_score * 25 +
            concentration_score * 10
        ) * 100
        
        # Determine risk level
        if overall_score >= 75:
            risk_level = "critical"
        elif overall_score >= 50:
            risk_level = "high"
        elif overall_score >= 25:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        return {
            "investigation_id": str(investigation_id),
            "overall_score": round(overall_score, 2),
            "risk_level": risk_level,
            "indicators": indicators,
            "factors": {k: round(v, 3) for k, v in factors.items()}
        }
    
    def _score_low_confidence(self, entities: List[CorrelatedEntity]) -> float:
        """Score based on entities with confidence < 0.7."""
        if not entities:
            return 0.0
        
        low_confidence_count = sum(1 for e in entities if e.confidence < 0.7)
        return min(low_confidence_count / max(len(entities), 1), 1.0)
    
    def _score_recent_registrations(self, entities: List[CorrelatedEntity]) -> float:
        """Score based on domains registered in last 90 days."""
        recent_count = 0
        total_domains = 0
        
        now = datetime.utcnow()
        threshold = now - timedelta(days=90)
        
        for entity in entities:
            if entity.entity_type == "domain":
                total_domains += 1
                for evidence in entity.evidence:
                    if evidence.occurred_at and evidence.occurred_at > threshold:
                        recent_count += 1
                        break
        
        if total_domains == 0:
            return 0.0
        
        return min(recent_count / total_domains, 1.0)
    
    def _score_privacy_protection(self, entities: List[CorrelatedEntity]) -> float:
        """Score based on use of privacy protection services."""
        privacy_keywords = ["privacy", "protected", "redacted", "whoisguard", "proxy"]
        
        privacy_count = 0
        total_relevant = 0
        
        for entity in entities:
            if entity.entity_type in ["registrar", "organization"]:
                total_relevant += 1
                value_lower = entity.primary_value.lower()
                if any(keyword in value_lower for keyword in privacy_keywords):
                    privacy_count += 1
        
        if total_relevant == 0:
            return 0.0
        
        return min(privacy_count / total_relevant, 1.0)
    
    def _score_shared_infrastructure(self, entities: CorrelatedEntities) -> float:
        """Score based on multiple domains sharing infrastructure."""
        domains = [e for e in entities.entities if e.entity_type == "domain"]
        
        if len(domains) < 2:
            return 0.0
        
        # Count domains sharing registrars or nameservers
        shared_count = 0
        for rel in entities.relationships:
            if rel.relationship_type in ["registered_with", "uses_nameserver"]:
                shared_count += 1
        
        max_possible = len(domains) * 2  # Each domain can have registrar + nameserver
        
        if max_possible == 0:
            return 0.0
        
        return min(shared_count / max_possible, 1.0)
    
    def _score_entity_concentration(self, entities: CorrelatedEntities) -> float:
        """Score based on relationship density."""
        entity_count = len(entities.entities)
        relationship_count = len(entities.relationships)
        
        if entity_count < 2:
            return 0.0
        
        max_relationships = entity_count * (entity_count - 1)
        
        if max_relationships == 0:
            return 0.0
        
        density = relationship_count / max_relationships
        
        return min(density * 2, 1.0)
