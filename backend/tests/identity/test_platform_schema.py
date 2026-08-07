"""
Tests for platform definition schema validation.
"""

import pytest
from pydantic import ValidationError

from app.identity.username.schema.platform_schema import (
    PlatformDefinition,
    validate_platform_definition,
    DetectionStrategyType,
)
from app.identity.types import PluginCategory, BackoffStrategy, RateLimitScope, CaptchaRisk, VerificationMethod


def test_valid_platform_definition():
    """Test a valid platform definition."""
    data = {
        "id": "test-platform",
        "display_name": "Test Platform",
        "category": "social",
        "homepage": "https://example.com",
        "profile_url_template": "https://example.com/user/{username}",
        "api_endpoint": "https://api.example.com/users/{username}",
        "detection": {
            "strategy": "json_api",
            "json_api": {
                "success_field": "$.id",
                "not_found_status": 404
            }
        },
        "network": {
            "timeout_seconds": 10,
            "retries": 2,
            "backoff": "exponential",
            "base_delay_ms": 500
        },
        "rate_limit": {
            "requests_per_minute": 30,
            "scope": "global"
        },
        "auth": {
            "login_required": False,
            "captcha_risk": "low"
        },
        "confidence_rules": {
            "base_reliability": 0.9,
            "verification_method": "api_confirmed",
            "corroboration_fields": ["avatar_url", "name"]
        },
        "parser": {
            "type": "json",
            "fields": {
                "display_name": "$.name",
                "avatar_url": "$.avatar"
            }
        },
        "enabled": True,
        "tags": ["test", "api"]
    }
    
    definition = validate_platform_definition(data)
    
    assert definition.id == "test-platform"
    assert definition.display_name == "Test Platform"
    assert definition.category == PluginCategory.SOCIAL
    assert definition.enabled is True


def test_missing_required_fields():
    """Test that missing required fields raise validation errors."""
    data = {
        "id": "test-platform",
        "display_name": "Test Platform"
        # Missing category, homepage, etc.
    }
    
    with pytest.raises(ValidationError):
        validate_platform_definition(data)


def test_invalid_id_format():
    """Test that invalid ID formats are rejected."""
    data = {
        "id": "Test-Platform-CAPS",  # Uppercase not allowed
        "display_name": "Test Platform",
        "category": "social",
        "homepage": "https://example.com",
        "profile_url_template": "https://example.com/user/{username}",
        "detection": {
            "strategy": "status_code",
            "status_code": {"success_codes": [200]}
        },
        "rate_limit": {"requests_per_minute": 30},
        "confidence_rules": {
            "base_reliability": 0.8,
            "verification_method": "api_confirmed"
        },
        "parser": {"type": "json"}
    }
    
    with pytest.raises(ValidationError, match="lowercase"):
        validate_platform_definition(data)


def test_profile_url_requires_username_placeholder():
    """Test that profile_url_template must contain {username}."""
    data = {
        "id": "test-platform",
        "display_name": "Test Platform",
        "category": "social",
        "homepage": "https://example.com",
        "profile_url_template": "https://example.com/user/",  # Missing {username}
        "detection": {
            "strategy": "status_code",
            "status_code": {"success_codes": [200]}
        },
        "rate_limit": {"requests_per_minute": 30},
        "confidence_rules": {
            "base_reliability": 0.8,
            "verification_method": "api_confirmed"
        },
        "parser": {"type": "json"}
    }
    
    with pytest.raises(ValidationError, match="username"):
        validate_platform_definition(data)


def test_api_endpoint_required_for_json_api_strategy():
    """Test that api_endpoint is required for json_api strategy."""
    data = {
        "id": "test-platform",
        "display_name": "Test Platform",
        "category": "social",
        "homepage": "https://example.com",
        "profile_url_template": "https://example.com/user/{username}",
        # api_endpoint missing
        "detection": {
            "strategy": "json_api",
            "json_api": {
                "success_field": "$.id",
                "not_found_status": 404
            }
        },
        "rate_limit": {"requests_per_minute": 30},
        "confidence_rules": {
            "base_reliability": 0.8,
            "verification_method": "api_confirmed"
        },
        "parser": {"type": "json"}
    }
    
    with pytest.raises(ValidationError, match="api_endpoint"):
        validate_platform_definition(data)


def test_strategy_config_required():
    """Test that appropriate config is required for the selected strategy."""
    data = {
        "id": "test-platform",
        "display_name": "Test Platform",
        "category": "social",
        "homepage": "https://example.com",
        "profile_url_template": "https://example.com/user/{username}",
        "detection": {
            "strategy": "json_api"
            # Missing json_api config
        },
        "rate_limit": {"requests_per_minute": 30},
        "confidence_rules": {
            "base_reliability": 0.8,
            "verification_method": "api_confirmed"
        },
        "parser": {"type": "json"}
    }
    
    with pytest.raises(ValidationError):
        validate_platform_definition(data)


def test_confidence_base_reliability_range():
    """Test that base_reliability must be between 0 and 1."""
    data = {
        "id": "test-platform",
        "display_name": "Test Platform",
        "category": "social",
        "homepage": "https://example.com",
        "profile_url_template": "https://example.com/user/{username}",
        "detection": {
            "strategy": "status_code",
            "status_code": {"success_codes": [200]}
        },
        "rate_limit": {"requests_per_minute": 30},
        "confidence_rules": {
            "base_reliability": 1.5,  # Invalid: > 1.0
            "verification_method": "api_confirmed"
        },
        "parser": {"type": "json"}
    }
    
    with pytest.raises(ValidationError):
        validate_platform_definition(data)


def test_platform_definition_methods():
    """Test utility methods on PlatformDefinition."""
    data = {
        "id": "test-platform",
        "display_name": "Test Platform",
        "category": "social",
        "homepage": "https://example.com",
        "profile_url_template": "https://example.com/user/{username}",
        "api_endpoint": "https://api.example.com/users/{username}",
        "detection": {
            "strategy": "json_api",
            "json_api": {
                "success_field": "$.id",
                "not_found_status": 404
            }
        },
        "rate_limit": {"requests_per_minute": 30},
        "confidence_rules": {
            "base_reliability": 0.9,
            "verification_method": "api_confirmed"
        },
        "parser": {"type": "json"}
    }
    
    definition = validate_platform_definition(data)
    
    # Test get_profile_url
    profile_url = definition.get_profile_url("testuser")
    assert profile_url == "https://example.com/user/testuser"
    
    # Test get_api_url
    api_url = definition.get_api_url("testuser")
    assert api_url == "https://api.example.com/users/testuser"


def test_extra_fields_forbidden():
    """Test that extra fields are rejected."""
    data = {
        "id": "test-platform",
        "display_name": "Test Platform",
        "category": "social",
        "homepage": "https://example.com",
        "profile_url_template": "https://example.com/user/{username}",
        "detection": {
            "strategy": "status_code",
            "status_code": {"success_codes": [200]}
        },
        "rate_limit": {"requests_per_minute": 30},
        "confidence_rules": {
            "base_reliability": 0.8,
            "verification_method": "api_confirmed"
        },
        "parser": {"type": "json"},
        "unknown_field": "should fail"  # Extra field
    }
    
    with pytest.raises(ValidationError, match="Extra inputs"):
        validate_platform_definition(data)
