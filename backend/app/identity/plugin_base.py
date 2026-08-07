"""
Base abstractions for the plugin system.

Defines the Plugin ABC and core data structures that all plugins implement.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from .types import (
    DetectionOutcomeExists,
    HealthStatus,
    IdentifierType,
    PluginCategory,
    VerificationMethod,
)


@dataclass
class PluginMetadata:
    """Metadata describing a plugin."""
    id: str
    display_name: str
    category: PluginCategory
    identifier_type: IdentifierType
    version: str
    enabled: bool
    description: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    homepage: Optional[str] = None


@dataclass
class ExecutionContext:
    """Context provided to a plugin during execution."""
    identifier_type: IdentifierType
    identifier_value: str
    investigation_id: UUID
    scan_id: UUID
    task_id: UUID
    options: dict[str, Any] = field(default_factory=dict)
    credentials: dict[str, Any] = field(default_factory=dict)
    
    # Runtime services injected by orchestrator
    http_client: Optional[Any] = None
    rate_limiter: Optional[Any] = None
    cache: Optional[Any] = None
    logger: Optional[Any] = None


@dataclass
class DetectionOutcome:
    """
    Result of a detection check for username platforms.
    
    This is the common return contract for all detection strategies.
    """
    exists: DetectionOutcomeExists
    http_status: Optional[int] = None
    evidence_fields: dict[str, Any] = field(default_factory=dict)
    raw_snapshot_ref: Optional[str] = None
    strategy_confidence_hint: float = 0.5
    
    def __post_init__(self):
        """Validate confidence hint is in valid range."""
        if not 0.0 <= self.strategy_confidence_hint <= 1.0:
            raise ValueError(f"strategy_confidence_hint must be between 0 and 1, got {self.strategy_confidence_hint}")


@dataclass
class RawResult:
    """
    Raw result from a plugin execution.
    
    This wraps the detection outcome or module-specific result
    with metadata about the execution.
    """
    plugin_id: str
    identifier_type: IdentifierType
    identifier_value: str
    success: bool
    timestamp: datetime
    
    # For username platforms: DetectionOutcome
    # For email/phone modules: module-specific dict
    payload: DetectionOutcome | dict[str, Any]
    
    error: Optional[str] = None
    duration_ms: Optional[float] = None
    http_status: Optional[int] = None
    raw_snapshot_ref: Optional[str] = None


@dataclass
class HealthCheckResult:
    """Result of a plugin health check."""
    status: HealthStatus
    timestamp: datetime
    message: Optional[str] = None
    latency_ms: Optional[float] = None
    details: dict[str, Any] = field(default_factory=dict)


class Plugin(ABC):
    """
    Abstract base class for all plugins.
    
    Plugins can be:
    - UsernamePlatformPlugin: wraps a PlatformDefinition, delegates to DetectionStrategy
    - EmailModulePlugin: email verification modules
    - PhoneModulePlugin: phone verification modules
    """
    
    @abstractmethod
    def describe(self) -> PluginMetadata:
        """Return metadata describing this plugin."""
        pass
    
    @abstractmethod
    async def execute(self, context: ExecutionContext) -> RawResult:
        """
        Execute the plugin's core logic.
        
        Args:
            context: Execution context with identifier, services, credentials
            
        Returns:
            RawResult containing the outcome and metadata
            
        Raises:
            Exception: Any error during execution (handled by orchestrator)
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> HealthCheckResult:
        """
        Perform a lightweight health check.
        
        Should use a known-good synthetic request to verify the platform/service
        is reachable and responding as expected.
        
        Returns:
            HealthCheckResult with status and details
        """
        pass
    
    @property
    def id(self) -> str:
        """Convenience property for plugin ID."""
        return self.describe().id
    
    @property
    def enabled(self) -> bool:
        """Convenience property for enabled status."""
        return self.describe().enabled


class UsernamePlatformPlugin(Plugin):
    """
    Base class for username platform plugins.
    
    These plugins wrap a PlatformDefinition and delegate detection
    to a DetectionStrategy at execution time.
    """
    pass


class EmailModulePlugin(Plugin):
    """
    Base class for email verification module plugins.
    
    Examples: Gravatar, MX lookup, breach check, disposable detection
    """
    pass


class PhoneModulePlugin(Plugin):
    """
    Base class for phone verification module plugins.
    
    Examples: parsing, validation, carrier lookup, messaging presence
    """
    pass
