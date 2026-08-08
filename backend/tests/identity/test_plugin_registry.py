"""
Tests for plugin registry and discovery system.
"""

import pytest

from app.identity.plugin_base import Plugin, PluginMetadata, ExecutionContext, RawResult, HealthCheckResult
from app.identity.plugin_runtime.registry import PluginRegistry, get_registry, reset_registry
from app.identity.types import HealthStatus, IdentifierType, PluginCategory


class MockPlugin(Plugin):
    """Mock plugin for testing."""
    
    def __init__(self, plugin_id: str, category: PluginCategory, tags: list[str] = None, enabled: bool = True):
        self._id = plugin_id
        self._category = category
        self._tags = tags or []
        self._enabled = enabled
    
    def describe(self) -> PluginMetadata:
        return PluginMetadata(
            id=self._id,
            display_name=f"Mock {self._id}",
            category=self._category,
            identifier_type=IdentifierType.USERNAME,
            version="1.0.0",
            enabled=self._enabled,
            tags=self._tags,
        )
    
    async def execute(self, context: ExecutionContext) -> RawResult:
        pass
    
    async def health_check(self) -> HealthCheckResult:
        pass


@pytest.fixture
def registry():
    """Provide a fresh registry for each test."""
    reset_registry()
    reg = PluginRegistry()
    yield reg
    reset_registry()


def test_plugin_registration(registry):
    """Test basic plugin registration."""
    plugin = MockPlugin("test-plugin", PluginCategory.SOCIAL)
    
    registry.register(plugin)
    
    assert "test-plugin" in registry.list_all()
    assert registry.get("test-plugin") == plugin


def test_duplicate_registration_fails(registry):
    """Test that duplicate plugin IDs are rejected."""
    plugin1 = MockPlugin("test-plugin", PluginCategory.SOCIAL)
    plugin2 = MockPlugin("test-plugin", PluginCategory.DEVELOPER)
    
    registry.register(plugin1)
    
    with pytest.raises(ValueError, match="already registered"):
        registry.register(plugin2)


def test_filter_by_identifier_type(registry):
    """Test filtering plugins by identifier type."""
    plugin1 = MockPlugin("social-1", PluginCategory.SOCIAL)
    plugin2 = MockPlugin("social-2", PluginCategory.SOCIAL)
    
    registry.register(plugin1)
    registry.register(plugin2)
    
    plugins = registry.list_by_identifier_type(IdentifierType.USERNAME)
    assert len(plugins) == 2
    assert "social-1" in plugins
    assert "social-2" in plugins


def test_filter_by_category(registry):
    """Test filtering plugins by category."""
    plugin1 = MockPlugin("social-1", PluginCategory.SOCIAL)
    plugin2 = MockPlugin("dev-1", PluginCategory.DEVELOPER)
    plugin3 = MockPlugin("social-2", PluginCategory.SOCIAL)
    
    registry.register(plugin1)
    registry.register(plugin2)
    registry.register(plugin3)
    
    social_plugins = registry.list_by_category(PluginCategory.SOCIAL)
    assert len(social_plugins) == 2
    assert "social-1" in social_plugins
    assert "social-2" in social_plugins


def test_filter_by_tags(registry):
    """Test filtering plugins by tags."""
    plugin1 = MockPlugin("plugin-1", PluginCategory.SOCIAL, tags=["high-confidence", "fast"])
    plugin2 = MockPlugin("plugin-2", PluginCategory.SOCIAL, tags=["high-confidence"])
    plugin3 = MockPlugin("plugin-3", PluginCategory.SOCIAL, tags=["fast"])
    
    registry.register(plugin1)
    registry.register(plugin2)
    registry.register(plugin3)
    
    # Test single tag (any match)
    high_conf = registry.list_by_tags(["high-confidence"])
    assert len(high_conf) == 2
    assert "plugin-1" in high_conf
    assert "plugin-2" in high_conf
    
    # Test multiple tags (any match)
    any_tag = registry.list_by_tags(["high-confidence", "fast"], match_all=False)
    assert len(any_tag) == 3
    
    # Test multiple tags (all must match)
    all_tags = registry.list_by_tags(["high-confidence", "fast"], match_all=True)
    assert len(all_tags) == 1
    assert "plugin-1" in all_tags


def test_enabled_only_filter(registry):
    """Test filtering for enabled plugins only."""
    plugin1 = MockPlugin("enabled-1", PluginCategory.SOCIAL, enabled=True)
    plugin2 = MockPlugin("disabled-1", PluginCategory.SOCIAL, enabled=False)
    plugin3 = MockPlugin("enabled-2", PluginCategory.SOCIAL, enabled=True)
    
    registry.register(plugin1)
    registry.register(plugin2)
    registry.register(plugin3)
    
    enabled = registry.list_enabled()
    assert len(enabled) == 2
    assert "enabled-1" in enabled
    assert "enabled-2" in enabled
    assert "disabled-1" not in enabled


def test_health_status_tracking(registry):
    """Test health status tracking."""
    plugin = MockPlugin("test-plugin", PluginCategory.SOCIAL)
    registry.register(plugin)
    
    # Initial status should be UNKNOWN
    assert registry.get_health_status("test-plugin") == HealthStatus.UNKNOWN
    
    # Update status
    registry.update_health_status("test-plugin", HealthStatus.HEALTHY)
    assert registry.get_health_status("test-plugin") == HealthStatus.HEALTHY
    
    registry.update_health_status("test-plugin", HealthStatus.DEGRADED)
    assert registry.get_health_status("test-plugin") == HealthStatus.DEGRADED


def test_get_statistics(registry):
    """Test registry statistics."""
    plugin1 = MockPlugin("plugin-1", PluginCategory.SOCIAL, enabled=True)
    plugin2 = MockPlugin("plugin-2", PluginCategory.DEVELOPER, enabled=False)
    
    registry.register(plugin1)
    registry.register(plugin2)
    registry.update_health_status("plugin-1", HealthStatus.HEALTHY)
    
    stats = registry.get_statistics()
    
    assert stats["total"] == 2
    assert stats["enabled"] == 1
    assert stats["disabled"] == 1
    assert stats["by_identifier_type"][IdentifierType.USERNAME] == 2
    assert stats["by_health_status"][HealthStatus.HEALTHY] == 1


def test_complex_filter(registry):
    """Test complex multi-criteria filtering."""
    plugin1 = MockPlugin("social-1", PluginCategory.SOCIAL, tags=["high-confidence"], enabled=True)
    plugin2 = MockPlugin("social-2", PluginCategory.SOCIAL, tags=["medium"], enabled=True)
    plugin3 = MockPlugin("dev-1", PluginCategory.DEVELOPER, tags=["high-confidence"], enabled=True)
    plugin4 = MockPlugin("social-3", PluginCategory.SOCIAL, tags=["high-confidence"], enabled=False)
    
    registry.register(plugin1)
    registry.register(plugin2)
    registry.register(plugin3)
    registry.register(plugin4)
    
    # Filter: social category + high-confidence tag + enabled only
    filtered = registry.filter_plugins(
        identifier_type=IdentifierType.USERNAME,
        category=PluginCategory.SOCIAL,
        tags=["high-confidence"],
        enabled_only=True
    )
    
    assert len(filtered) == 1
    assert "social-1" in filtered


def test_unregister_plugin(registry):
    """Test unregistering a plugin."""
    plugin = MockPlugin("test-plugin", PluginCategory.SOCIAL)
    registry.register(plugin)
    
    assert "test-plugin" in registry.list_all()
    
    registry.unregister("test-plugin")
    
    assert "test-plugin" not in registry.list_all()
    assert registry.get("test-plugin") is None
