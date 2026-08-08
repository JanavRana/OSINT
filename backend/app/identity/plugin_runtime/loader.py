"""
Plugin loader for dynamic discovery and initialization.

Supports:
- Directory scanning for platform definition files (YAML)
- Python module scanning for email/phone plugins
- Validation before registration
- Safe error handling with detailed logging
"""

import logging
from pathlib import Path
from typing import Optional

import yaml

from ..plugin_base import Plugin
from .registry import PluginRegistry

logger = logging.getLogger(__name__)


class PluginLoader:
    """
    Discovers and loads plugins from various sources.
    
    For username platforms: scans YAML files
    For email/phone modules: imports Python modules
    """
    
    def __init__(self, registry: PluginRegistry):
        self.registry = registry
        self._loaded_paths: set[Path] = set()
    
    def load_yaml_file(self, path: Path) -> Optional[dict]:
        """
        Load and parse a YAML file.
        
        Args:
            path: Path to YAML file
            
        Returns:
            Parsed YAML content as dict, or None if failed
        """
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if not isinstance(data, dict):
                logger.error(f"Invalid YAML file {path}: root must be a dictionary")
                return None
            
            return data
        
        except yaml.YAMLError as e:
            logger.error(f"Failed to parse YAML file {path}: {e}")
            return None
        
        except Exception as e:
            logger.error(f"Failed to load YAML file {path}: {e}")
            return None
    
    def load_platform_definition(self, path: Path, validator=None) -> Optional[str]:
        """
        Load a platform definition from a YAML file.
        
        Args:
            path: Path to platform definition YAML
            validator: Optional callable to create plugin from validated definition
            
        Returns:
            Plugin ID if successfully loaded, None otherwise
        """
        if path in self._loaded_paths:
            logger.debug(f"Platform definition already loaded: {path}")
            return None
        
        data = self.load_yaml_file(path)
        if data is None:
            return None
        
        try:
            # If validator provided, use it to create and validate plugin
            if validator:
                plugin = validator(data)
                self.registry.register(plugin)
                self._loaded_paths.add(path)
                return plugin.id
            else:
                # Just validate the structure without creating plugin
                platform_id = data.get('id')
                if not platform_id:
                    logger.error(f"Platform definition {path} missing 'id' field")
                    return None
                
                logger.debug(f"Validated platform definition: {platform_id}")
                self._loaded_paths.add(path)
                return platform_id
        
        except ValueError as e:
            logger.error(f"Validation failed for {path}: {e}")
            return None
        
        except Exception as e:
            logger.error(f"Failed to load platform definition {path}: {e}", exc_info=True)
            return None
    
    def scan_platform_directory(
        self, 
        directory: Path, 
        pattern: str = "*.yaml",
        validator=None
    ) -> dict[str, str]:
        """
        Scan a directory for platform definition files.
        
        Args:
            directory: Directory to scan
            pattern: Glob pattern for files to load
            validator: Optional callable to create plugins
            
        Returns:
            Dictionary mapping file paths to plugin IDs (or error messages)
        """
        if not directory.exists():
            logger.warning(f"Platform directory does not exist: {directory}")
            return {}
        
        if not directory.is_dir():
            logger.error(f"Platform path is not a directory: {directory}")
            return {}
        
        results = {}
        
        for yaml_file in directory.glob(pattern):
            if not yaml_file.is_file():
                continue
            
            try:
                plugin_id = self.load_platform_definition(yaml_file, validator)
                if plugin_id:
                    results[str(yaml_file)] = plugin_id
                    logger.info(f"Loaded platform: {plugin_id} from {yaml_file.name}")
                else:
                    results[str(yaml_file)] = "ERROR: Failed to load"
            
            except Exception as e:
                logger.error(f"Error loading {yaml_file}: {e}", exc_info=True)
                results[str(yaml_file)] = f"ERROR: {e}"
        
        return results
    
    def load_plugin_module(self, module_path: str, plugin_class_name: str) -> Optional[str]:
        """
        Dynamically import and register a plugin from a Python module.
        
        Args:
            module_path: Dotted path to module (e.g., 'app.identity.email.modules.gravatar')
            plugin_class_name: Name of plugin class to instantiate
            
        Returns:
            Plugin ID if successfully loaded, None otherwise
        """
        try:
            # Dynamic import
            from importlib import import_module
            
            module = import_module(module_path)
            plugin_class = getattr(module, plugin_class_name, None)
            
            if plugin_class is None:
                logger.error(f"Plugin class '{plugin_class_name}' not found in {module_path}")
                return None
            
            # Instantiate and register
            plugin = plugin_class()
            if not isinstance(plugin, Plugin):
                logger.error(f"{plugin_class_name} does not inherit from Plugin")
                return None
            
            self.registry.register(plugin)
            logger.info(f"Loaded plugin module: {plugin.id} from {module_path}")
            return plugin.id
        
        except ImportError as e:
            logger.error(f"Failed to import module {module_path}: {e}")
            return None
        
        except Exception as e:
            logger.error(f"Failed to load plugin from {module_path}: {e}", exc_info=True)
            return None
    
    def load_registry_file(self, registry_path: Path, base_dir: Path, validator=None) -> dict:
        """
        Load a registry file that lists platform definitions to enable.
        
        The registry file format:
        ```yaml
        platforms:
          - github.yaml
          - gitlab.yaml
          - reddit.yaml
        ```
        
        Args:
            registry_path: Path to registry YAML file
            base_dir: Base directory where platform files are located
            validator: Optional callable to create plugins
            
        Returns:
            Dictionary with load results
        """
        data = self.load_yaml_file(registry_path)
        if data is None:
            return {"error": "Failed to load registry file"}
        
        platforms = data.get('platforms', [])
        if not isinstance(platforms, list):
            logger.error(f"Registry file 'platforms' must be a list")
            return {"error": "Invalid registry format"}
        
        results = {
            "total": len(platforms),
            "loaded": 0,
            "failed": 0,
            "details": {}
        }
        
        for platform_file in platforms:
            platform_path = base_dir / platform_file
            
            plugin_id = self.load_platform_definition(platform_path, validator)
            if plugin_id:
                results["loaded"] += 1
                results["details"][platform_file] = {"status": "loaded", "id": plugin_id}
            else:
                results["failed"] += 1
                results["details"][platform_file] = {"status": "failed"}
        
        logger.info(
            f"Registry load complete: {results['loaded']}/{results['total']} platforms loaded"
        )
        
        return results
    
    def get_loaded_paths(self) -> list[Path]:
        """Get list of paths that have been successfully loaded."""
        return list(self._loaded_paths)
    
    def clear_loaded_paths(self) -> None:
        """Clear the set of loaded paths. Mainly for testing."""
        self._loaded_paths.clear()


def create_loader(registry: Optional[PluginRegistry] = None) -> PluginLoader:
    """
    Create a plugin loader instance.
    
    Args:
        registry: Optional registry to use, otherwise uses global registry
        
    Returns:
        PluginLoader instance
    """
    from .registry import get_registry
    
    if registry is None:
        registry = get_registry()
    
    return PluginLoader(registry)
