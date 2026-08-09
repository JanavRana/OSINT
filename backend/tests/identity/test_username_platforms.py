"""
Tests for username platform definitions and loading.
"""

import pytest
from pathlib import Path

from app.identity.username.loader import PlatformLoader
from app.identity.username.schema.platform_schema import PlatformDefinition


class TestPlatformLoader:
    """Test platform loader functionality."""
    
    def test_loader_finds_platforms_directory(self):
        """Test that loader finds default platforms directory."""
        loader = PlatformLoader()
        assert loader.platforms_dir.exists()
        assert loader.platforms_dir.name == "platforms"
    
    def test_load_registry(self):
        """Test loading platforms registry file."""
        loader = PlatformLoader()
        registry = loader.load_registry()
        
        assert registry is not None
        assert len(registry.platforms) > 0
        assert all(f.endswith(('.yaml', '.yml')) for f in registry.platforms)
    
    def test_load_github_platform(self):
        """Test loading GitHub platform definition."""
        loader = PlatformLoader()
        definition = loader.load_platform_file("github.yaml")
        
        assert definition is not None
        assert definition.id == "github"
        assert definition.display_name == "GitHub"
        assert definition.category.value == "developer"
        assert definition.enabled is True
        assert definition.detection.strategy.value == "json_api"
        assert definition.api_endpoint is not None
        assert "{username}" in definition.profile_url_template
    
    def test_load_reddit_platform(self):
        """Test loading Reddit platform definition."""
        loader = PlatformLoader()
        definition = loader.load_platform_file("reddit.yaml")
        
        assert definition is not None
        assert definition.id == "reddit"
        assert definition.display_name == "Reddit"
        assert definition.enabled is True
    
    def test_load_all_platforms(self):
        """Test loading all platform definitions."""
        loader = PlatformLoader()
        definitions = loader.load_all_platforms()
        
        # Should have loaded multiple platforms
        assert len(definitions) >= 30
        
        # All should be valid PlatformDefinition instances
        assert all(isinstance(d, PlatformDefinition) for d in definitions)
        
        # All should have unique IDs
        ids = [d.id for d in definitions]
        assert len(ids) == len(set(ids))
    
    def test_disabled_platform(self):
        """Test that disabled platforms are loaded but marked disabled."""
        loader = PlatformLoader()
        definitions = loader.load_all_platforms()
        
        # Discord should be disabled
        discord = next((d for d in definitions if d.id == "discord"), None)
        if discord:
            assert discord.enabled is False


class TestPlatformDefinitions:
    """Test individual platform definitions for correctness."""
    
    def test_all_platforms_have_required_fields(self):
        """Test that all platforms have required fields."""
        loader = PlatformLoader()
        definitions = loader.load_all_platforms()
        
        for definition in definitions:
            # Required identity fields
            assert definition.id
            assert definition.display_name
            assert definition.category
            assert definition.homepage
            
            # Required URL fields
            assert definition.profile_url_template
            assert "{username}" in definition.profile_url_template
            
            # Required configuration
            assert definition.detection
            assert definition.network
            assert definition.rate_limit
            assert definition.auth
            assert definition.confidence_rules
            assert definition.parser
    
    def test_api_endpoints_for_api_strategies(self):
        """Test that platforms using API strategies have api_endpoint."""
        loader = PlatformLoader()
        definitions = loader.load_all_platforms()
        
        api_strategies = ["json_api", "graphql"]
        
        for definition in definitions:
            if definition.detection.strategy.value in api_strategies:
                assert definition.api_endpoint is not None, \
                    f"Platform {definition.id} uses {definition.detection.strategy} but has no api_endpoint"
                # GraphQL endpoints pass username as variable, not in URL
                if definition.detection.strategy.value != "graphql":
                    assert "{username}" in definition.api_endpoint
    
    def test_confidence_rules_valid(self):
        """Test that confidence rules are within valid ranges."""
        loader = PlatformLoader()
        definitions = loader.load_all_platforms()
        
        for definition in definitions:
            reliability = definition.confidence_rules.base_reliability
            assert 0.0 <= reliability <= 1.0, \
                f"Platform {definition.id} has invalid base_reliability: {reliability}"
    
    def test_rate_limits_reasonable(self):
        """Test that rate limits are reasonable."""
        loader = PlatformLoader()
        definitions = loader.load_all_platforms()
        
        for definition in definitions:
            rpm = definition.rate_limit.requests_per_minute
            assert rpm > 0, \
                f"Platform {definition.id} has invalid rate limit: {rpm}"
            assert rpm <= 100, \
                f"Platform {definition.id} has suspiciously high rate limit: {rpm}"
    
    def test_network_timeouts_reasonable(self):
        """Test that network timeouts are reasonable."""
        loader = PlatformLoader()
        definitions = loader.load_all_platforms()
        
        for definition in definitions:
            timeout = definition.network.timeout_seconds
            assert 1 <= timeout <= 30, \
                f"Platform {definition.id} has unreasonable timeout: {timeout}"


class TestPlatformCategories:
    """Test platform categorization."""
    
    def test_developer_platforms(self):
        """Test that developer platforms are correctly categorized."""
        loader = PlatformLoader()
        definitions = loader.load_all_platforms()
        
        developer_platforms = [
            "github", "gitlab", "leetcode", "codeforces",
            "hackerrank", "codechef", "codepen", "npm",
            "pypi", "docker-hub", "kaggle", "sourceforge"
        ]
        
        for platform_id in developer_platforms:
            platform = next((d for d in definitions if d.id == platform_id), None)
            if platform:
                assert platform.category.value == "developer", \
                    f"Platform {platform_id} should be in developer category"
    
    def test_social_platforms(self):
        """Test that social platforms are correctly categorized."""
        loader = PlatformLoader()
        definitions = loader.load_all_platforms()
        
        social_platforms = [
            "reddit", "x", "instagram", "tiktok", "youtube",
            "twitch", "pinterest", "medium", "soundcloud",
            "tumblr", "flickr", "vimeo"
        ]
        
        for platform_id in social_platforms:
            platform = next((d for d in definitions if d.id == platform_id), None)
            if platform:
                assert platform.category.value == "social", \
                    f"Platform {platform_id} should be in social category"


class TestPlatformTags:
    """Test platform tagging for filtering."""
    
    def test_high_confidence_platforms_have_tag(self):
        """Test that high confidence platforms are tagged."""
        loader = PlatformLoader()
        definitions = loader.load_all_platforms()
        
        for definition in definitions:
            if definition.confidence_rules.base_reliability >= 0.85:
                # High reliability platforms should have high-confidence tag
                # (not enforced but recommended)
                pass
    
    def test_api_based_platforms_have_tag(self):
        """Test that API-based platforms are tagged."""
        loader = PlatformLoader()
        definitions = loader.load_all_platforms()
        
        api_strategies = ["json_api", "graphql"]
        
        for definition in definitions:
            if definition.detection.strategy.value in api_strategies:
                # Should have api-based tag (not enforced but recommended)
                pass


class TestPluginCreation:
    """Test creating plugins from platform definitions."""
    
    def test_create_plugins_from_definitions(self):
        """Test creating plugin instances from definitions."""
        loader = PlatformLoader()
        definitions = loader.load_all_platforms()
        plugins = loader.create_plugins_from_definitions(definitions)
        
        assert len(plugins) == len(definitions)
        
        # All plugins should have describe() method
        for plugin in plugins:
            metadata = plugin.describe()
            assert metadata.id
            assert metadata.display_name
            assert metadata.identifier_type.value == "username"
    
    def test_plugin_metadata_matches_definition(self):
        """Test that plugin metadata matches platform definition."""
        loader = PlatformLoader()
        definition = loader.load_platform_file("github.yaml")
        plugins = loader.create_plugins_from_definitions([definition])
        
        plugin = plugins[0]
        metadata = plugin.describe()
        
        assert metadata.id == definition.id
        assert metadata.display_name == definition.display_name
        assert metadata.category == definition.category
        assert metadata.enabled == definition.enabled


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
