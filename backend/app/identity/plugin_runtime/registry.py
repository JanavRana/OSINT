"""
Plugin registry for discovery, registration, and lifecycle management.

The registry maintains the set of available plugins and provides
query/filtering capabilities for the orchestrator.
"""

import logging
from collections import defaultdict
from typing import Optional

from ..plugin_base import Plugin, PluginMetadata
from ..types import HealthStatus, IdentifierType, PluginCategory

logger = logging.getLogger(__name__)


class PluginRegistry:
    """
    Central registry for all plugins.
    
    Responsibilities:
    - Plugin registration and validation
    - Duplicate ID detection
    - Query/filtering by identifier type, category, tags
    - Health status tracking
    - Enable/disable management
    """
    
    def __init__(self):
        self._plugins: dict[str, Plugin] = {}
        self._metadata_cache: dict[str, PluginMetadata] = {}
        self._health_status: dict[str, HealthStatus] = {}
        
        # Indexes for fast lookups
        self._by_identifier_type: dict[IdentifierType, set[str]] = defaultdict(set)
        self._by_category: dict[PluginCategory, set[str]] = defaultdict(set)
        self._by_tag: dict[str, set[str]] = defaultdict(set)
    
    def register(self, plugin: Plugin) -> None:
        """
        Register a plugin with the registry.
        
        Args:
            plugin: Plugin instance to register
            
        Raises:
            ValueError: If plugin ID is already registered or validation fails
        """
        metadata = plugin.describe()
        
        # Validate plugin ID
        if not metadata.id:
            raise ValueError("Plugin ID cannot be empty")
        
        if metadata.id in self._plugins:
            raise ValueError(f"Plugin with ID '{metadata.id}' is already registered")
        
        # Register plugin
        self._plugins[metadata.id] = plugin
        self._metadata_cache[metadata.id] = metadata
        self._health_status[metadata.id] = HealthStatus.UNKNOWN
        
        # Update indexes
        self._by_identifier_type[metadata.identifier_type].add(metadata.id)
        self._by_category[metadata.category].add(metadata.id)
        for tag in metadata.tags:
            self._by_tag[tag].add(metadata.id)
        
        logger.info(
            f"Registered plugin: {metadata.id} "
            f"(type={metadata.identifier_type}, category={metadata.category}, enabled={metadata.enabled})"
        )
    
    def unregister(self, plugin_id: str) -> None:
        """
        Unregister a plugin from the registry.
        
        Args:
            plugin_id: ID of plugin to unregister
        """
        if plugin_id not in self._plugins:
            logger.warning(f"Attempted to unregister unknown plugin: {plugin_id}")
            return
        
        metadata = self._metadata_cache[plugin_id]
        
        # Remove from indexes
        self._by_identifier_type[metadata.identifier_type].discard(plugin_id)
        self._by_category[metadata.category].discard(plugin_id)
        for tag in metadata.tags:
            self._by_tag[tag].discard(plugin_id)
        
        # Remove from registry
        del self._plugins[plugin_id]
        del self._metadata_cache[plugin_id]
        del self._health_status[plugin_id]
        
        logger.info(f"Unregistered plugin: {plugin_id}")
    
    def get(self, plugin_id: str) -> Optional[Plugin]:
        """Get a plugin by ID."""
        return self._plugins.get(plugin_id)
    
    def get_metadata(self, plugin_id: str) -> Optional[PluginMetadata]:
        """Get cached metadata for a plugin."""
        return self._metadata_cache.get(plugin_id)
    
    def get_health_status(self, plugin_id: str) -> Optional[HealthStatus]:
        """Get the health status of a plugin."""
        return self._health_status.get(plugin_id)
    
    def update_health_status(self, plugin_id: str, status: HealthStatus) -> None:
        """Update the health status of a plugin."""
        if plugin_id in self._plugins:
            self._health_status[plugin_id] = status
            logger.debug(f"Updated health status for {plugin_id}: {status}")
    
    def list_all(self) -> list[str]:
        """List all registered plugin IDs."""
        return list(self._plugins.keys())
    
    def list_enabled(self) -> list[str]:
        """List all enabled plugin IDs."""
        return [
            plugin_id 
            for plugin_id, metadata in self._metadata_cache.items()
            if metadata.enabled
        ]
    
    def list_by_identifier_type(
        self, 
        identifier_type: IdentifierType,
        enabled_only: bool = True
    ) -> list[str]:
        """
        List plugins by identifier type.
        
        Args:
            identifier_type: Type of identifier (username, email, phone)
            enabled_only: If True, only return enabled plugins
            
        Returns:
            List of plugin IDs
        """
        plugin_ids = self._by_identifier_type.get(identifier_type, set())
        
        if enabled_only:
            plugin_ids = {
                pid for pid in plugin_ids 
                if self._metadata_cache.get(pid, {}).enabled
            }
        
        return list(plugin_ids)
    
    def list_by_category(
        self,
        category: PluginCategory,
        enabled_only: bool = True
    ) -> list[str]:
        """
        List plugins by category.
        
        Args:
            category: Plugin category
            enabled_only: If True, only return enabled plugins
            
        Returns:
            List of plugin IDs
        """
        plugin_ids = self._by_category.get(category, set())
        
        if enabled_only:
            plugin_ids = {
                pid for pid in plugin_ids
                if self._metadata_cache.get(pid, {}).enabled
            }
        
        return list(plugin_ids)
    
    def list_by_tags(
        self,
        tags: list[str],
        match_all: bool = False,
        enabled_only: bool = True
    ) -> list[str]:
        """
        List plugins by tags.
        
        Args:
            tags: List of tags to match
            match_all: If True, plugin must have all tags; if False, any tag matches
            enabled_only: If True, only return enabled plugins
            
        Returns:
            List of plugin IDs
        """
        if not tags:
            return []
        
        if match_all:
            # Intersection: plugin must have all tags
            plugin_ids = set(self._by_tag.get(tags[0], set()))
            for tag in tags[1:]:
                plugin_ids &= self._by_tag.get(tag, set())
        else:
            # Union: plugin has any of the tags
            plugin_ids = set()
            for tag in tags:
                plugin_ids |= self._by_tag.get(tag, set())
        
        if enabled_only:
            plugin_ids = {
                pid for pid in plugin_ids
                if self._metadata_cache.get(pid, {}).enabled
            }
        
        return list(plugin_ids)
    
    def filter_plugins(
        self,
        identifier_type: Optional[IdentifierType] = None,
        category: Optional[PluginCategory] = None,
        tags: Optional[list[str]] = None,
        match_all_tags: bool = False,
        enabled_only: bool = True,
        healthy_only: bool = False
    ) -> list[str]:
        """
        Filter plugins by multiple criteria.
        
        Args:
            identifier_type: Filter by identifier type
            category: Filter by category
            tags: Filter by tags
            match_all_tags: If True, plugin must have all tags
            enabled_only: If True, only return enabled plugins
            healthy_only: If True, only return healthy/unknown status plugins
            
        Returns:
            List of plugin IDs matching all criteria
        """
        # Start with all plugins
        result = set(self._plugins.keys())
        
        # Apply filters progressively
        if identifier_type:
            if isinstance(identifier_type, str):
                try:
                    identifier_type = IdentifierType(identifier_type)
                except ValueError:
                    pass
            result &= self._by_identifier_type.get(identifier_type, set())
        
        if category:
            if isinstance(category, str):
                try:
                    category = PluginCategory(category)
                except ValueError:
                    pass
            result &= self._by_category.get(category, set())
        
        if tags:
            tag_matches = set(self.list_by_tags(tags, match_all=match_all_tags, enabled_only=False))
            result &= tag_matches
        
        if enabled_only:
            result = {
                pid for pid in result
                if self._metadata_cache.get(pid, {}).enabled
            }
        
        if healthy_only:
            result = {
                pid for pid in result
                if self._health_status.get(pid) in (HealthStatus.HEALTHY, HealthStatus.UNKNOWN)
            }
        
        return list(result)
    
    def get_statistics(self) -> dict:
        """
        Get registry statistics.
        
        Returns:
            Dictionary with counts and breakdowns
        """
        total = len(self._plugins)
        enabled = len(self.list_enabled())
        
        by_type = {
            itype: len(self._by_identifier_type.get(itype, set()))
            for itype in IdentifierType
        }
        
        by_category = {
            cat: len(self._by_category.get(cat, set()))
            for cat in PluginCategory
        }
        
        by_health = defaultdict(int)
        for status in self._health_status.values():
            by_health[status] += 1
        
        return {
            "total": total,
            "enabled": enabled,
            "disabled": total - enabled,
            "by_identifier_type": by_type,
            "by_category": by_category,
            "by_health_status": dict(by_health),
        }
    
    def clear(self) -> None:
        """Clear all plugins from the registry. Mainly for testing."""
        self._plugins.clear()
        self._metadata_cache.clear()
        self._health_status.clear()
        self._by_identifier_type.clear()
        self._by_category.clear()
        self._by_tag.clear()
        logger.info("Registry cleared")


# Global singleton instance
_registry: Optional[PluginRegistry] = None


def get_registry() -> PluginRegistry:
    """Get the global plugin registry instance."""
    global _registry
    if _registry is None:
        _registry = PluginRegistry()
    return _registry


def reset_registry() -> None:
    """Reset the global registry. Mainly for testing."""
    global _registry
    if _registry:
        _registry.clear()
    _registry = None
