"""
Integration tests for username OSINT system.

Tests the complete flow from platform loading to normalization.
"""

import pytest
from uuid import uuid4

from app.identity.username.loader import PlatformLoader
from app.identity.username.init import (
    get_enabled_platforms,
    get_platform_count,
)


class TestUsernameIntegration:
    """Integration tests for complete username OSINT flow."""
    
    def test_load_and_count_platforms(self):
        """Test loading platforms and getting counts."""
        loader = PlatformLoader()
        definitions = loader.load_all_platforms()
        
        assert len(definitions) >= 30, "Should have at least 30 platforms"
        
        counts = get_platform_count()
        assert counts["total"] >= 30
        assert counts["enabled"] >= 25
        assert counts["disabled"] >= 0
        assert counts["total"] == counts["enabled"] + counts["disabled"]
    
    def test_enabled_platforms_list(self):
        """Test getting list of enabled platforms."""
        enabled = get_enabled_platforms()
        
        assert isinstance(enabled, list)
        assert len(enabled) >= 25
        
        # GitHub should be enabled
        assert "github" in enabled
        
        # Discord should not be enabled (marked disabled)
        assert "discord" not in enabled
    
    def test_platform_diversity(self):
        """Test that platforms cover multiple categories."""
        loader = PlatformLoader()
        definitions = loader.load_all_platforms()
        
        categories = set(d.category.value for d in definitions)
        
        # Should have multiple categories
        assert "developer" in categories
        assert "social" in categories
        assert "professional" in categories or "creative" in categories
    
    def test_detection_strategy_diversity(self):
        """Test that multiple detection strategies are used."""
        loader = PlatformLoader()
        definitions = loader.load_all_platforms()
        
        strategies = set(d.detection.strategy.value for d in definitions)
        
        # Should use multiple strategies
        assert "json_api" in strategies
        assert "status_code" in strategies
        # May also have graphql, html_parse, etc.
    
    def test_high_confidence_platforms(self):
        """Test that we have high-confidence platforms."""
        loader = PlatformLoader()
        definitions = loader.load_all_platforms()
        
        high_confidence = [
            d for d in definitions
            if d.confidence_rules.base_reliability >= 0.85
            and d.enabled
        ]
        
        assert len(high_confidence) >= 10, \
            "Should have at least 10 high-confidence enabled platforms"
        
        # Known high-confidence platforms
        high_conf_ids = [d.id for d in high_confidence]
        assert "github" in high_conf_ids
        assert "gitlab" in high_conf_ids or "reddit" in high_conf_ids
    
    def test_api_based_platforms(self):
        """Test that we have API-based platforms."""
        loader = PlatformLoader()
        definitions = loader.load_all_platforms()
        
        api_strategies = ["json_api", "graphql"]
        api_platforms = [
            d for d in definitions
            if d.detection.strategy.value in api_strategies
            and d.enabled
        ]
        
        assert len(api_platforms) >= 8, \
            "Should have at least 8 API-based enabled platforms"
    
    def test_no_duplicate_platform_ids(self):
        """Test that all platform IDs are unique."""
        loader = PlatformLoader()
        definitions = loader.load_all_platforms()
        
        ids = [d.id for d in definitions]
        assert len(ids) == len(set(ids)), \
            "Platform IDs must be unique"
    
    def test_all_platforms_have_valid_urls(self):
        """Test that all platform URLs are well-formed."""
        loader = PlatformLoader()
        definitions = loader.load_all_platforms()
        
        for definition in definitions:
            # Profile URL should have username placeholder
            assert "{username}" in definition.profile_url_template, \
                f"Platform {definition.id} missing username placeholder"
            
            # API endpoint should have placeholder if present (except GraphQL)
            if definition.api_endpoint and definition.detection.strategy.value != "graphql":
                assert "{username}" in definition.api_endpoint, \
                    f"Platform {definition.id} API endpoint missing username placeholder"


class TestPlatformRobustness:
    """Test robustness and error handling."""
    
    def test_invalid_platform_file_skipped(self):
        """Test that invalid platform files are skipped gracefully."""
        loader = PlatformLoader()
        
        # Try to load a non-existent file
        result = loader.load_platform_file("nonexistent_platform.yaml")
        
        # Should return None, not raise exception
        assert result is None
    
    def test_partial_platform_loading(self):
        """Test that valid platforms load even if some fail."""
        loader = PlatformLoader()
        definitions = loader.load_all_platforms()
        
        # Should have loaded many platforms despite any failures
        assert len(definitions) >= 30


class TestFalsePositiveProtection:
    """Test false positive protection mechanisms."""
    
    def test_explicit_not_found_high_confidence(self):
        """Test that explicit 404s have high confidence."""
        from app.identity.plugin_base import DetectionOutcome, RawResult
        from app.identity.types import IdentifierType
        from app.identity.username.normalizer import normalize_username_result
        from datetime import datetime
        
        investigation_id = uuid4()
        
        outcome = DetectionOutcome(
            exists=False,
            http_status=404,
            strategy_confidence_hint=0.9
        )
        
        raw_result = RawResult(
            plugin_id="github",
            identifier_type=IdentifierType.USERNAME,
            identifier_value="definitely_not_exists_xyz123",
            success=True,
            timestamp=datetime.utcnow(),
            payload=outcome,
            http_status=404
        )
        
        fact = normalize_username_result(raw_result, investigation_id)
        
        # Explicit 404 should have high confidence
        assert fact.confidence.value >= 0.8
    
    def test_ambiguous_results_lower_confidence(self):
        """Test that ambiguous results have lower confidence."""
        from app.identity.plugin_base import DetectionOutcome, RawResult
        from app.identity.types import IdentifierType
        from app.identity.username.normalizer import normalize_username_result
        from datetime import datetime
        
        investigation_id = uuid4()
        
        outcome = DetectionOutcome(
            exists="unknown",
            http_status=200,
            strategy_confidence_hint=0.5
        )
        
        raw_result = RawResult(
            plugin_id="someplatform",
            identifier_type=IdentifierType.USERNAME,
            identifier_value="ambiguous_user",
            success=True,
            timestamp=datetime.utcnow(),
            payload=outcome,
            http_status=200
        )
        
        fact = normalize_username_result(raw_result, investigation_id)
        
        # Ambiguous/unknown results should have lower confidence
        assert fact.confidence.value < 0.7


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
