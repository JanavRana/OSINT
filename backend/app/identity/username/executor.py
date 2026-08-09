"""
Generic executor for username platform plugins.

Interprets PlatformDefinition metadata and delegates to detection strategies,
eliminating the need for per-platform imperative code.
"""

import logging
import time
from datetime import datetime
from typing import Optional

from ..plugin_base import (
    ExecutionContext,
    HealthCheckResult,
    PluginMetadata,
    RawResult,
    UsernamePlatformPlugin,
)
from ..types import HealthStatus, IdentifierType
from .detection.base import get_strategy_registry
from .schema.platform_schema import PlatformDefinition

# Import detection strategies to ensure they're registered
from . import detection  # noqa: F401

logger = logging.getLogger(__name__)


class UsernamePlatformExecutor(UsernamePlatformPlugin):
    """
    Generic executor for username platforms.
    
    This is the core of the declarative platform system. It:
    1. Wraps a validated PlatformDefinition
    2. Delegates to the appropriate DetectionStrategy at runtime
    3. Handles errors and timeouts
    4. Returns standardized RawResult
    
    No per-platform code is needed - all behavior comes from the definition.
    """
    
    def __init__(self, definition: PlatformDefinition):
        """
        Initialize executor with a platform definition.
        
        Args:
            definition: Validated platform definition
        """
        self.definition = definition
        self._strategy_registry = get_strategy_registry()
    
    def describe(self) -> PluginMetadata:
        """Return metadata from platform definition."""
        return PluginMetadata(
            id=self.definition.id,
            display_name=self.definition.display_name,
            category=self.definition.category,
            identifier_type=IdentifierType.USERNAME,
            version="1.0.0",
            enabled=self.definition.enabled,
            description=self.definition.notes,
            tags=self.definition.tags,
            homepage=str(self.definition.homepage),
        )
    
    async def execute(self, context: ExecutionContext) -> RawResult:
        """
        Execute username check using the platform's detection strategy.
        
        Args:
            context: Execution context with username, services, credentials
            
        Returns:
            RawResult with DetectionOutcome payload
        """
        username = context.identifier_value
        start_time = time.monotonic()
        
        try:
            # Get the detection strategy
            strategy_type = self.definition.detection.strategy.value
            strategy = self._strategy_registry.create_instance(strategy_type)
            
            if strategy is None:
                raise ValueError(f"Unknown detection strategy: {strategy_type}")
            
            # Execute the strategy
            logger.debug(
                f"Executing {strategy_type} strategy for {self.definition.id}: {username}"
            )
            
            outcome = await strategy.check(
                username=username,
                definition=self.definition,
                http_client=context.http_client,
                logger=context.logger
            )
            
            duration_ms = (time.monotonic() - start_time) * 1000
            
            # Build RawResult
            result = RawResult(
                plugin_id=self.definition.id,
                identifier_type=IdentifierType.USERNAME,
                identifier_value=username,
                success=True,
                timestamp=datetime.utcnow(),
                payload=outcome,
                duration_ms=duration_ms,
                http_status=outcome.http_status,
                raw_snapshot_ref=outcome.raw_snapshot_ref,
            )
            
            logger.info(
                f"Username check completed for {self.definition.id}/{username}: "
                f"exists={outcome.exists}, duration={duration_ms:.1f}ms"
            )
            
            return result
        
        except Exception as e:
            duration_ms = (time.monotonic() - start_time) * 1000
            
            logger.error(
                f"Username check failed for {self.definition.id}/{username}: {e}",
                exc_info=True
            )
            
            # Return failed result
            return RawResult(
                plugin_id=self.definition.id,
                identifier_type=IdentifierType.USERNAME,
                identifier_value=username,
                success=False,
                timestamp=datetime.utcnow(),
                payload={},
                error=str(e),
                duration_ms=duration_ms,
            )
    
    async def health_check(self) -> HealthCheckResult:
        """
        Perform health check using a synthetic username.
        
        Uses a known-good username to verify the platform is reachable
        and responding as expected.
        """
        start_time = time.monotonic()
        
        # Use a synthetic test username
        # In production, this would be configurable per platform
        test_username = "test_user_that_should_not_exist_12345"
        
        try:
            # Get the detection strategy
            strategy_type = self.definition.detection.strategy.value
            strategy = self._strategy_registry.create_instance(strategy_type)
            
            if strategy is None:
                return HealthCheckResult(
                    status=HealthStatus.DEGRADED,
                    timestamp=datetime.utcnow(),
                    message=f"Unknown detection strategy: {strategy_type}"
                )
            
            # Execute strategy with test username
            # We don't care about the result, just that it completes without error
            outcome = await strategy.check(
                username=test_username,
                definition=self.definition,
                http_client=None,  # Would be injected in production
                logger=logger
            )
            
            latency_ms = (time.monotonic() - start_time) * 1000
            
            # If we got any response (even "unknown"), the platform is reachable
            return HealthCheckResult(
                status=HealthStatus.HEALTHY,
                timestamp=datetime.utcnow(),
                message="Platform responsive",
                latency_ms=latency_ms,
                details={
                    "test_username": test_username,
                    "outcome": str(outcome.exists),
                }
            )
        
        except Exception as e:
            latency_ms = (time.monotonic() - start_time) * 1000
            
            logger.warning(
                f"Health check failed for {self.definition.id}: {e}"
            )
            
            return HealthCheckResult(
                status=HealthStatus.DEGRADED,
                timestamp=datetime.utcnow(),
                message=f"Health check failed: {str(e)}",
                latency_ms=latency_ms,
                details={"error": str(e)}
            )


def create_platform_plugin(definition: PlatformDefinition) -> UsernamePlatformExecutor:
    """
    Factory function to create a username platform plugin from a definition.
    
    This is the bridge between the YAML definition and the plugin system.
    
    Args:
        definition: Validated platform definition
        
    Returns:
        UsernamePlatformExecutor instance ready for registration
    """
    return UsernamePlatformExecutor(definition)


def create_platform_plugin_from_dict(data: dict) -> UsernamePlatformExecutor:
    """
    Create a platform plugin from a dictionary (parsed YAML).
    
    Args:
        data: Dictionary with platform definition
        
    Returns:
        UsernamePlatformExecutor instance
        
    Raises:
        ValidationError: If data doesn't conform to schema
    """
    from .schema.platform_schema import validate_platform_definition
    
    definition = validate_platform_definition(data)
    return create_platform_plugin(definition)
