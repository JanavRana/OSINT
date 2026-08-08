"""
Core types and enums for the identity OSINT subsystem.
"""

from enum import Enum
from typing import Literal


class IdentifierType(str, Enum):
    """Type of identifier being investigated."""
    USERNAME = "username"
    EMAIL = "email"
    PHONE = "phone"


class PluginCategory(str, Enum):
    """Category classification for plugins."""
    SOCIAL = "social"
    DEVELOPER = "developer"
    GAMING = "gaming"
    PROFESSIONAL = "professional"
    CREATIVE = "creative"
    FORUM = "forum"
    OTHER = "other"


class VerificationMethod(str, Enum):
    """Method used to verify a fact."""
    API_CONFIRMED = "api_confirmed"
    GRAPHQL_CONFIRMED = "graphql_confirmed"
    HTML_SCRAPE = "html_scrape"
    REDIRECT_INFERENCE = "redirect_inference"
    DNS_LOOKUP = "dns_lookup"
    SMTP_VERIFICATION = "smtp_verification"
    CARRIER_LOOKUP = "carrier_lookup"
    PRESENCE_CHECK = "presence_check"


class HealthStatus(str, Enum):
    """Health status of a plugin."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


class CircuitBreakerState(str, Enum):
    """State of a circuit breaker."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class ScanStatus(str, Enum):
    """Status of a scan operation."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_PARTIAL_FAILURES = "completed_with_partial_failures"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
    FAILED = "failed"


class TaskStatus(str, Enum):
    """Status of an individual scan task."""
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED_CIRCUIT_OPEN = "skipped_circuit_open"
    SKIPPED_DISABLED = "skipped_disabled"
    CANCELLED = "cancelled"


class CaptchaRisk(str, Enum):
    """CAPTCHA risk level for a platform."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class BackoffStrategy(str, Enum):
    """Backoff strategy for retries."""
    NONE = "none"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"


class RateLimitScope(str, Enum):
    """Scope of rate limiting."""
    GLOBAL = "global"
    PER_API_KEY = "per_api_key"
    PER_TENANT = "per_tenant"


DetectionOutcomeExists = Literal[True, False, "unknown"]
