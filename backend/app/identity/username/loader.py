"""
Platform loader for username OSINT.

Loads platform definitions from YAML files, validates them,
and creates plugin instances for the registry.
"""

import logging
from pathlib import Path
from typing import Optional

import yaml
from pydantic import ValidationError

from .executor import create_platform_plugin
from .schema.platform_schema import PlatformDefinition, PlatformRegistry

logger = logging.getLogger(__name__)


class PlatformLoader:
    """
    Loads and validates platform definitions from YAML files.
    
    This is the bridge between the YAML config files and the plugin system.
    """
    
    def __init__(self, platforms_dir: Optional[Path] = None):
        """
        Initialize loader.
        
        Args:
            platforms_dir: Directory containing platform YAML files.
                          Defaults to platforms/ subdirectory of this module.
        """
        if platforms_dir is None:
            # Default to platforms/ directory next to this file
            platforms_dir = Path(__file__).parent / "platforms"
        
        self.platforms_dir = Path(platforms_dir)
        
        if not self.platforms_dir.exists():
            raise ValueError(f"Platforms directory does not exist: {self.platforms_dir}")
    
    def load_registry(self) -> PlatformRegistry:
        """
        Load the platform registry file.
        
        Returns:
            PlatformRegistry with list of platform files to load
            
        Raises:
            FileNotFoundError: If registry file doesn't exist
            ValidationError: If registry file is invalid
        """
        registry_path = self.platforms_dir / "platforms.registry.yaml"
        
        if not registry_path.exists():
            raise FileNotFoundError(f"Registry file not found: {registry_path}")
        
        with open(registry_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        return PlatformRegistry.model_validate(data)
    
    def load_platform_file(self, filename: str) -> Optional[PlatformDefinition]:
        """
        Load and validate a single platform definition file.
        
        Args:
            filename: Platform YAML filename
            
        Returns:
            Validated PlatformDefinition, or None if loading failed
        """
        file_path = self.platforms_dir / filename
        
        if not file_path.exists():
            logger.error(f"Platform file not found: {file_path}")
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            # Validate against schema
            definition = PlatformDefinition.model_validate(data)
            
            logger.info(
                f"Loaded platform '{definition.id}' from {filename} "
                f"(enabled={definition.enabled})"
            )
            
            return definition
        
        except ValidationError as e:
            logger.error(
                f"Platform file '{filename}' failed validation: {e}",
                exc_info=True
            )
            return None
        
        except yaml.YAMLError as e:
            logger.error(
                f"Failed to parse YAML file '{filename}': {e}",
                exc_info=True
            )
            return None
        
        except Exception as e:
            logger.error(
                f"Unexpected error loading platform file '{filename}': {e}",
                exc_info=True
            )
            return None
    
    def load_all_platforms(self) -> list[PlatformDefinition]:
        """
        Load all platform definitions listed in the registry.
        
        Returns:
            List of successfully loaded PlatformDefinition instances
            (excludes any that failed validation)
        """
        try:
            registry = self.load_registry()
        except Exception as e:
            logger.error(f"Failed to load platform registry: {e}")
            return []
        
        platforms = []
        failed_count = 0
        
        for filename in registry.platforms:
            definition = self.load_platform_file(filename)
            
            if definition:
                platforms.append(definition)
            else:
                failed_count += 1
        
        logger.info(
            f"Loaded {len(platforms)} platform(s), {failed_count} failed"
        )
        
        return platforms
    
    def create_plugins_from_definitions(
        self,
        definitions: list[PlatformDefinition]
    ) -> list:
        """
        Create plugin instances from platform definitions.
        
        Args:
            definitions: List of validated platform definitions
            
        Returns:
            List of UsernamePlatformExecutor instances
        """
        plugins = []
        
        for definition in definitions:
            try:
                plugin = create_platform_plugin(definition)
                plugins.append(plugin)
                
                logger.debug(
                    f"Created plugin for platform '{definition.id}'"
                )
            
            except Exception as e:
                logger.error(
                    f"Failed to create plugin for platform '{definition.id}': {e}",
                    exc_info=True
                )
        
        return plugins


def load_username_platforms(platforms_dir: Optional[Path] = None):
    """
    Convenience function to load all username platforms.
    
    Args:
        platforms_dir: Optional directory containing platform files
        
    Returns:
        Tuple of (plugins, definitions) - plugins for registration,
        definitions for reference
    """
    loader = PlatformLoader(platforms_dir)
    definitions = loader.load_all_platforms()
    plugins = loader.create_plugins_from_definitions(definitions)
    
    logger.info(f"Loaded {len(plugins)} username platform plugins")
    
    return plugins, definitions


def register_username_platforms(registry, platforms_dir: Optional[Path] = None) -> int:
    """
    Load and register all username platforms with the plugin registry.
    
    Args:
        registry: Plugin registry instance
        platforms_dir: Optional directory containing platform files
        
    Returns:
        Number of platforms successfully registered
    """
    plugins, _ = load_username_platforms(platforms_dir)
    
    registered_count = 0
    
    for plugin in plugins:
        try:
            registry.register(plugin)
            registered_count += 1
            
            logger.debug(f"Registered platform plugin: {plugin.id}")
        
        except Exception as e:
            logger.error(
                f"Failed to register plugin '{plugin.id}': {e}",
                exc_info=True
            )
    
    logger.info(
        f"Registered {registered_count}/{len(plugins)} username platforms"
    )
    
    return registered_count
