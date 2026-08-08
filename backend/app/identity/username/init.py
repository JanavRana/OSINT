"""
Initialization module for username OSINT platforms.

Loads platform definitions and registers them with the plugin registry on startup.
"""

import logging
from pathlib import Path

from ..plugin_runtime.registry import get_registry
from .loader import register_username_platforms

logger = logging.getLogger(__name__)


def initialize_username_platforms(platforms_dir: Path | None = None) -> int:
    """
    Initialize username platforms by loading definitions and registering plugins.
    
    This should be called during application startup.
    
    Args:
        platforms_dir: Optional custom platforms directory
        
    Returns:
        Number of platforms successfully registered
    """
    logger.info("Initializing username OSINT platforms...")
    
    try:
        registry = get_registry()
        count = register_username_platforms(registry, platforms_dir)
        
        logger.info(f"Successfully initialized {count} username platforms")
        return count
    
    except Exception as e:
        logger.error(f"Failed to initialize username platforms: {e}", exc_info=True)
        return 0


def get_enabled_platforms() -> list[str]:
    """
    Get list of enabled platform IDs.
    
    Returns:
        List of platform IDs that are currently enabled
    """
    registry = get_registry()
    plugins = registry.filter_plugins(
        identifier_type="username",
        enabled_only=True
    )
    return [p.id for p in plugins]


def get_platform_count() -> dict[str, int]:
    """
    Get count of registered platforms by status.
    
    Returns:
        Dict with 'total', 'enabled', 'disabled' counts
    """
    registry = get_registry()
    all_plugins = registry.filter_plugins(identifier_type="username")
    enabled_plugins = registry.filter_plugins(
        identifier_type="username",
        enabled_only=True
    )
    
    return {
        "total": len(all_plugins),
        "enabled": len(enabled_plugins),
        "disabled": len(all_plugins) - len(enabled_plugins),
    }
