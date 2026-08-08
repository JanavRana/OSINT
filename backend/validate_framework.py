"""
Validation script for Intel Weave plugin framework.

Tests that all core components can be instantiated and basic operations work.
"""

import asyncio
from uuid import uuid4

def test_types():
    """Test type enums."""
    from app.identity.types import (
        IdentifierType, PluginCategory, VerificationMethod,
        HealthStatus, CircuitBreakerState, ScanStatus, TaskStatus
    )
    
    print("✓ All type enums defined correctly")
    assert IdentifierType.USERNAME
    assert PluginCategory.SOCIAL
    assert VerificationMethod.API_CONFIRMED

def test_plugin_base():
    """Test plugin base abstractions."""
    from app.identity.plugin_base import (
        PluginMetadata, ExecutionContext, DetectionOutcome, RawResult
    )
    
    print("✓ Plugin base abstractions defined")

def test_plugin_registry():
    """Test plugin registry."""
    from app.identity.plugin_runtime.registry import PluginRegistry
    from app.identity.types import IdentifierType, PluginCategory
    
    registry = PluginRegistry()
    stats = registry.get_statistics()
    
    print(f"✓ Plugin registry initialized (total plugins: {stats['total']})")

def test_rate_limiter():
    """Test rate limiter."""
    from app.identity.plugin_runtime.rate_limiter import RateLimiter
    
    limiter = RateLimiter()
    limiter.configure("test-plugin", requests_per_minute=60)
    
    assert limiter.try_acquire("test-plugin") is True
    print("✓ Rate limiter configured and working")

def test_cache():
    """Test cache."""
    from app.identity.plugin_runtime.cache import Cache
    
    cache = Cache(max_size=100)
    cache.configure_plugin_ttl("test-plugin", 3600)
    
    stats = cache.get_statistics()
    print(f"✓ Cache initialized (size: {stats['size']}/{stats['max_size']})")

async def test_circuit_breaker():
    """Test circuit breaker."""
    from app.identity.plugin_runtime.circuit_breaker import (
        CircuitBreaker, CircuitBreakerConfig
    )
    from app.identity.types import CircuitBreakerState
    
    config = CircuitBreakerConfig()
    breaker = CircuitBreaker("test-plugin", config)
    
    assert breaker.state == CircuitBreakerState.CLOSED
    assert await breaker.is_call_allowed() is True
    
    print("✓ Circuit breaker initialized and working")

def test_platform_schema():
    """Test platform definition schema."""
    from app.identity.username.schema.platform_schema import (
        validate_platform_definition
    )
    
    definition_data = {
        "id": "test-platform",
        "display_name": "Test Platform",
        "category": "social",
        "homepage": "https://example.com",
        "profile_url_template": "https://example.com/user/{username}",
        "detection": {
            "strategy": "status_code",
            "status_code": {
                "success_codes": [200],
                "not_found_codes": [404]
            }
        },
        "network": {
            "timeout_seconds": 10,
            "retries": 2,
            "backoff": "exponential",
            "base_delay_ms": 250
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
            "base_reliability": 0.85,
            "verification_method": "api_confirmed"
        },
        "parser": {
            "type": "json"
        }
    }
    
    definition = validate_platform_definition(definition_data)
    assert definition.id == "test-platform"
    
    print(f"✓ Platform schema validation working (platform: {definition.display_name})")

def test_detection_strategies():
    """Test detection strategies are registered."""
    # Import strategies module to trigger decorator registration
    from app.identity.username.detection import strategies as _
    from app.identity.username.detection.base import get_strategy_registry
    
    registry = get_strategy_registry()
    strategies = registry.list_strategies()
    
    assert "status_code" in strategies
    assert "json_api" in strategies
    assert "html_parse" in strategies
    
    print(f"✓ Detection strategies registered: {', '.join(strategies)}")

def test_username_executor():
    """Test username executor can be created."""
    from app.identity.username.executor import create_platform_plugin_from_dict
    
    definition_data = {
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
            "base_reliability": 0.85,
            "verification_method": "api_confirmed"
        },
        "parser": {"type": "json"}
    }
    
    plugin = create_platform_plugin_from_dict(definition_data)
    metadata = plugin.describe()
    
    assert metadata.id == "test-platform"
    print(f"✓ Username executor created (plugin: {metadata.display_name})")

def test_orchestrator():
    """Test orchestrator components."""
    from app.identity.orchestrator.planner import ScanPlanner
    from app.identity.orchestrator.concurrency import ConcurrencyGovernor
    from app.identity.orchestrator.checkpoint_store import CheckpointStore
    from app.identity.plugin_runtime.registry import PluginRegistry
    from app.identity.types import IdentifierType
    
    registry = PluginRegistry()
    planner = ScanPlanner(registry)
    governor = ConcurrencyGovernor(global_limit=200)
    store = CheckpointStore()
    
    # Test planning a scan
    plan = planner.plan_scan(
        investigation_id=uuid4(),
        identifier_type=IdentifierType.USERNAME,
        identifier_value="testuser"
    )
    
    assert plan.identifier_value == "testuser"
    print(f"✓ Orchestrator components working (scan planned: {plan.scan_id})")

def test_confidence_engine():
    """Test confidence engine."""
    from app.identity.confidence.engine import ConfidenceEngine
    from app.identity.types import VerificationMethod
    from datetime import datetime
    
    engine = ConfidenceEngine()
    
    score = engine.calculate_score(
        source_reliability=0.9,
        verification_method=VerificationMethod.API_CONFIRMED,
        corroboration_count=1,
        observed_at=datetime.utcnow(),
        plugin_success_rate=0.95
    )
    
    assert 0.0 <= score.value <= 1.0
    print(f"✓ Confidence engine working (sample score: {score.value:.3f})")

def test_evidence_models():
    """Test evidence and normalized fact models."""
    from app.identity.evidence.models import (
        Evidence, NormalizedFact, create_username_platform_fact
    )
    from app.identity.confidence.engine import ConfidenceScore, ConfidenceFactors
    from app.identity.types import VerificationMethod
    from datetime import datetime
    
    evidence = Evidence(
        source_plugin_id="test-platform",
        verification_method=VerificationMethod.API_CONFIRMED,
        observed_at=datetime.utcnow()
    )
    
    confidence = ConfidenceScore(
        value=0.9,
        factors=ConfidenceFactors(
            source_reliability=0.9,
            verification_method=0.95,
            corroboration=0.8,
            freshness=1.0,
            historical_success=0.9
        )
    )
    
    fact = create_username_platform_fact(
        investigation_id=uuid4(),
        username="testuser",
        platform_id="test-platform",
        exists=True,
        evidence_fields={"display_name": "Test User"},
        evidence=evidence,
        confidence=confidence
    )
    
    assert fact.identifier_value == "testuser"
    print(f"✓ Evidence models working (fact type: {fact.fact_type})")

async def run_async_tests():
    """Run async tests."""
    await test_circuit_breaker()

def main():
    """Run all validation tests."""
    print("=" * 60)
    print("Intel Weave Plugin Framework Validation")
    print("=" * 60)
    print()
    
    try:
        # Synchronous tests
        test_types()
        test_plugin_base()
        test_plugin_registry()
        test_rate_limiter()
        test_cache()
        test_platform_schema()
        test_detection_strategies()
        test_username_executor()
        test_orchestrator()
        test_confidence_engine()
        test_evidence_models()
        
        # Async tests
        asyncio.run(run_async_tests())
        
        print()
        print("=" * 60)
        print("✅ All validation tests passed!")
        print("=" * 60)
        print()
        print("Framework components verified:")
        print("  • Plugin base abstractions")
        print("  • Plugin registry and discovery")
        print("  • Platform schema validation")
        print("  • Detection strategies")
        print("  • Username generic executor")
        print("  • Rate limiter")
        print("  • Cache")
        print("  • Circuit breaker")
        print("  • Orchestrator (planner, concurrency, checkpoint)")
        print("  • Confidence engine")
        print("  • Evidence and normalized fact models")
        print()
        print("The framework is ready for platform implementations!")
        
        return 0
    
    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ Validation failed: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())
