"""
Base detection strategy interface.

All detection strategies implement this ABC and return DetectionOutcome.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional

from ...plugin_base import DetectionOutcome
from ..schema.platform_schema import PlatformDefinition


class DetectionStrategy(ABC):
    """
    Abstract base class for username detection strategies.
    
    Each strategy implements a different method for checking if a username
    exists on a platform (status code, redirect, regex, API, etc.)
    """
    
    @abstractmethod
    async def check(
        self,
        username: str,
        definition: PlatformDefinition,
        http_client: Any,
        logger: Optional[Any] = None
    ) -> DetectionOutcome:
        """
        Check if a username exists on the platform.
        
        Args:
            username: Username to check
            definition: Platform definition with configuration
            http_client: HTTP client for making requests
            logger: Optional logger instance
            
        Returns:
            DetectionOutcome with exists status and evidence
            
        Raises:
            Exception: Any error during detection (handled by executor)
        """
        pass
    
    def _build_url(self, username: str, definition: PlatformDefinition, use_api: bool = False) -> str:
        """
        Build URL for the username check.
        
        Args:
            username: Username to check
            definition: Platform definition
            use_api: If True, use API endpoint; otherwise use profile URL
            
        Returns:
            Formatted URL
        """
        if use_api and definition.api_endpoint:
            return definition.get_api_url(username)
        return definition.get_profile_url(username)
    
    def _get_headers(self, definition: PlatformDefinition) -> dict[str, str]:
        """
        Build HTTP headers for the request.
        
        Args:
            definition: Platform definition with network config
            
        Returns:
            Dictionary of HTTP headers
        """
        headers = dict(definition.network.headers)
        
        if definition.network.user_agent:
            headers['User-Agent'] = definition.network.user_agent
        elif 'User-Agent' not in headers:
            # Default user agent
            headers['User-Agent'] = (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
        
        return headers
    
    def _get_timeout(self, definition: PlatformDefinition) -> float:
        """Get request timeout from definition."""
        return float(definition.network.timeout_seconds)


class DetectionStrategyRegistry:
    """
    Registry for detection strategies.
    
    Maps strategy type names to strategy implementations.
    """
    
    def __init__(self):
        self._strategies: dict[str, type[DetectionStrategy]] = {}
    
    def register(self, name: str, strategy_class: type[DetectionStrategy]) -> None:
        """Register a detection strategy."""
        self._strategies[name] = strategy_class
    
    def get(self, name: str) -> Optional[type[DetectionStrategy]]:
        """Get a strategy class by name."""
        return self._strategies.get(name)
    
    def list_strategies(self) -> list[str]:
        """List all registered strategy names."""
        return list(self._strategies.keys())
    
    def create_instance(self, name: str) -> Optional[DetectionStrategy]:
        """Create an instance of a strategy by name."""
        strategy_class = self.get(name)
        if strategy_class:
            return strategy_class()
        return None


# Global registry instance
_strategy_registry: Optional[DetectionStrategyRegistry] = None


def get_strategy_registry() -> DetectionStrategyRegistry:
    """Get the global strategy registry."""
    global _strategy_registry
    if _strategy_registry is None:
        _strategy_registry = DetectionStrategyRegistry()
    return _strategy_registry


def register_strategy(name: str):
    """
    Decorator to register a detection strategy.
    
    Usage:
        @register_strategy('status_code')
        class StatusCodeStrategy(DetectionStrategy):
            ...
    """
    def decorator(cls: type[DetectionStrategy]):
        registry = get_strategy_registry()
        registry.register(name, cls)
        return cls
    return decorator
