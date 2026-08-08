"""
Pydantic schema for declarative username platform definitions.

Each platform is defined in a YAML file validated against these schemas.
"""

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator

from ...types import BackoffStrategy, CaptchaRisk, PluginCategory, RateLimitScope, VerificationMethod


class DetectionStrategyType(str, Enum):
    """Type of detection strategy to use."""
    STATUS_CODE = "status_code"
    REDIRECT = "redirect"
    REGEX = "regex_body"
    JSON_API = "json_api"
    GRAPHQL = "graphql"
    HTML_PARSE = "html_parse"
    CUSTOM = "custom"


class ParserType(str, Enum):
    """Type of response parser."""
    JSON = "json"
    HTML = "html"
    TEXT = "text"
    NONE = "none"


# Detection Strategy Configurations

class StatusCodeDetectionConfig(BaseModel):
    """Configuration for status code detection strategy."""
    success_codes: list[int] = Field(default=[200], description="HTTP status codes indicating existence")
    not_found_codes: list[int] = Field(default=[404], description="HTTP status codes indicating non-existence")


class RedirectDetectionConfig(BaseModel):
    """Configuration for redirect-based detection strategy."""
    success_pattern: Optional[str] = Field(None, description="Regex pattern for successful redirect URL")
    not_found_pattern: Optional[str] = Field(None, description="Regex pattern for not-found redirect URL")
    max_redirects: int = Field(default=5, description="Maximum redirects to follow")


class RegexDetectionConfig(BaseModel):
    """Configuration for regex body detection strategy."""
    exists_pattern: Optional[str] = Field(None, description="Regex indicating profile exists")
    not_exists_pattern: Optional[str] = Field(None, description="Regex indicating profile does not exist")
    case_insensitive: bool = Field(default=True, description="Case-insensitive matching")


class JsonApiDetectionConfig(BaseModel):
    """Configuration for JSON API detection strategy."""
    success_field: str = Field(..., description="JSON field that must exist (JSONPath syntax)")
    not_found_status: int = Field(default=404, description="HTTP status for not found")
    error_field: Optional[str] = Field(None, description="JSON field indicating error")


class GraphQLDetectionConfig(BaseModel):
    """Configuration for GraphQL detection strategy."""
    query: str = Field(..., description="GraphQL query with {username} placeholder")
    success_field: str = Field(..., description="Field in response indicating existence")
    variables: dict[str, Any] = Field(default_factory=dict, description="Additional GraphQL variables")


class HtmlParseDetectionConfig(BaseModel):
    """Configuration for HTML parse detection strategy."""
    exists_selector: str = Field(..., description="CSS selector indicating profile exists")
    not_exists_pattern: Optional[str] = Field(None, description="Text pattern indicating not found")
    use_javascript: bool = Field(default=False, description="Whether JavaScript rendering is needed")


class CustomDetectionConfig(BaseModel):
    """Configuration for custom detection logic."""
    handler_id: str = Field(..., description="ID of registered custom handler")
    config: dict[str, Any] = Field(default_factory=dict, description="Handler-specific configuration")


class DetectionConfig(BaseModel):
    """
    Detection configuration for a platform.
    
    The strategy field determines which config fields are required.
    """
    strategy: DetectionStrategyType = Field(..., description="Detection strategy to use")
    
    # Strategy-specific configs (only one will be populated based on strategy)
    status_code: Optional[StatusCodeDetectionConfig] = None
    redirect: Optional[RedirectDetectionConfig] = None
    regex: Optional[RegexDetectionConfig] = None
    json_api: Optional[JsonApiDetectionConfig] = None
    graphql: Optional[GraphQLDetectionConfig] = None
    html_parse: Optional[HtmlParseDetectionConfig] = None
    custom: Optional[CustomDetectionConfig] = None
    
    @model_validator(mode='after')
    def validate_strategy_config(self):
        """Ensure the appropriate config is provided for the selected strategy."""
        strategy_map = {
            DetectionStrategyType.STATUS_CODE: self.status_code,
            DetectionStrategyType.REDIRECT: self.redirect,
            DetectionStrategyType.REGEX: self.regex,
            DetectionStrategyType.JSON_API: self.json_api,
            DetectionStrategyType.GRAPHQL: self.graphql,
            DetectionStrategyType.HTML_PARSE: self.html_parse,
            DetectionStrategyType.CUSTOM: self.custom,
        }
        
        config = strategy_map.get(self.strategy)
        if config is None:
            raise ValueError(f"Missing configuration for strategy '{self.strategy}'")
        
        return self


class NetworkConfig(BaseModel):
    """Network configuration for platform requests."""
    timeout_seconds: int = Field(default=8, ge=1, le=30, description="Request timeout in seconds")
    retries: int = Field(default=2, ge=0, le=5, description="Number of retries on failure")
    backoff: BackoffStrategy = Field(default=BackoffStrategy.EXPONENTIAL, description="Retry backoff strategy")
    base_delay_ms: int = Field(default=250, ge=0, description="Base delay for backoff in milliseconds")
    user_agent: Optional[str] = Field(None, description="Custom User-Agent header")
    headers: dict[str, str] = Field(default_factory=dict, description="Additional HTTP headers")


class RateLimitConfig(BaseModel):
    """Rate limiting configuration."""
    requests_per_minute: int = Field(..., gt=0, description="Maximum requests per minute")
    scope: RateLimitScope = Field(default=RateLimitScope.GLOBAL, description="Rate limit scope")
    burst_size: Optional[int] = Field(None, description="Burst allowance (defaults to requests_per_minute)")


class AuthConfig(BaseModel):
    """Authentication and access configuration."""
    login_required: bool = Field(default=False, description="Whether login/credentials are required")
    captcha_risk: CaptchaRisk = Field(default=CaptchaRisk.LOW, description="CAPTCHA risk level")
    api_key_required: bool = Field(default=False, description="Whether API key is needed")
    oauth_required: bool = Field(default=False, description="Whether OAuth is needed")


class ConfidenceRules(BaseModel):
    """Confidence scoring rules for this platform."""
    base_reliability: float = Field(..., ge=0.0, le=1.0, description="Base reliability score")
    verification_method: VerificationMethod = Field(..., description="Verification method used")
    corroboration_fields: list[str] = Field(
        default_factory=list, 
        description="Fields that can corroborate with other platforms"
    )


class ParserConfig(BaseModel):
    """Configuration for parsing platform responses."""
    type: ParserType = Field(..., description="Type of parser to use")
    fields: dict[str, str] = Field(
        default_factory=dict,
        description="Field mappings (field_name -> extraction_path). JSONPath for JSON, CSS selector for HTML"
    )
    
    @field_validator('fields')
    @classmethod
    def validate_fields(cls, v: dict[str, str]) -> dict[str, str]:
        """Validate field extraction paths."""
        for field_name, path in v.items():
            if not path:
                raise ValueError(f"Extraction path for field '{field_name}' cannot be empty")
        return v


class PlatformDefinition(BaseModel):
    """
    Complete platform definition schema.
    
    This is the root schema that all YAML platform files must conform to.
    """
    # Identity
    id: str = Field(..., description="Unique platform identifier (kebab-case)")
    display_name: str = Field(..., description="Human-readable platform name")
    category: PluginCategory = Field(..., description="Platform category")
    homepage: HttpUrl = Field(..., description="Platform homepage URL")
    
    # URLs
    profile_url_template: str = Field(
        ..., 
        description="Profile URL template with {username} placeholder"
    )
    api_endpoint: Optional[str] = Field(
        None,
        description="API endpoint template (required for json_api/graphql strategies)"
    )
    
    # Configuration sections
    detection: DetectionConfig = Field(..., description="Detection strategy configuration")
    network: NetworkConfig = Field(default_factory=NetworkConfig, description="Network configuration")
    rate_limit: RateLimitConfig = Field(..., description="Rate limiting configuration")
    auth: AuthConfig = Field(default_factory=AuthConfig, description="Authentication configuration")
    confidence_rules: ConfidenceRules = Field(..., description="Confidence scoring rules")
    parser: ParserConfig = Field(..., description="Response parser configuration")
    
    # Metadata
    normalizer: str = Field(
        default="username.normalizer.default",
        description="Dotted path to normalizer function"
    )
    enabled: bool = Field(default=True, description="Whether platform is enabled")
    tags: list[str] = Field(default_factory=list, description="Tags for filtering/search")
    notes: Optional[str] = Field(None, description="Internal notes about the platform")
    
    @field_validator('id')
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Validate platform ID format."""
        if not v:
            raise ValueError("Platform ID cannot be empty")
        
        # Check for valid kebab-case
        if not all(c.islower() or c.isdigit() or c in ('-', '_') for c in v):
            raise ValueError(
                f"Platform ID must be lowercase with hyphens/underscores only: {v}"
            )
        
        return v
    
    @field_validator('profile_url_template')
    @classmethod
    def validate_profile_url(cls, v: str) -> str:
        """Ensure profile URL template contains {username} placeholder."""
        if '{username}' not in v:
            raise ValueError("profile_url_template must contain {username} placeholder")
        return v
    
    @model_validator(mode='after')
    def validate_api_endpoint_requirement(self):
        """Ensure api_endpoint is provided when required by strategy."""
        strategies_requiring_api = {
            DetectionStrategyType.JSON_API,
            DetectionStrategyType.GRAPHQL,
        }
        
        if self.detection.strategy in strategies_requiring_api and not self.api_endpoint:
            raise ValueError(
                f"api_endpoint is required for {self.detection.strategy} strategy"
            )
        
        return self
    
    @model_validator(mode='after')
    def validate_api_endpoint_placeholder(self):
        """Ensure api_endpoint contains {username} placeholder if present."""
        # GraphQL endpoints pass username as variable, not in URL
        if self.detection.strategy != DetectionStrategyType.GRAPHQL:
            if self.api_endpoint and '{username}' not in self.api_endpoint:
                raise ValueError("api_endpoint must contain {username} placeholder")
        
        return self
    
    def get_profile_url(self, username: str) -> str:
        """Generate profile URL for a given username."""
        return self.profile_url_template.format(username=username)
    
    def get_api_url(self, username: str) -> Optional[str]:
        """Generate API URL for a given username."""
        if self.api_endpoint:
            return self.api_endpoint.format(username=username)
        return None
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = False
        validate_assignment = True
        extra = 'forbid'  # Reject unknown fields in YAML


class PlatformRegistry(BaseModel):
    """
    Schema for the platforms registry file.
    
    Lists which platform definition files should be loaded.
    """
    platforms: list[str] = Field(
        ...,
        description="List of platform YAML filenames to load"
    )
    
    @field_validator('platforms')
    @classmethod
    def validate_platforms(cls, v: list[str]) -> list[str]:
        """Validate platform filenames."""
        for filename in v:
            if not filename.endswith(('.yaml', '.yml')):
                raise ValueError(f"Platform file must be YAML: {filename}")
        return v


def validate_platform_definition(data: dict) -> PlatformDefinition:
    """
    Validate platform definition data against schema.
    
    Args:
        data: Raw dictionary from YAML file
        
    Returns:
        Validated PlatformDefinition instance
        
    Raises:
        ValidationError: If data doesn't conform to schema
    """
    return PlatformDefinition.model_validate(data)
