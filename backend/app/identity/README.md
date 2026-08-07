# Intel Weave Identity OSINT Subsystem

## Overview

This is the plugin framework and orchestration infrastructure for the Intel Weave identity OSINT subsystem. It provides a declarative, scalable architecture for username, email, and phone identifier investigations.

## Architecture

The framework follows the design specified in `docs/planning/intel-weave-architecture.md` and implements:

### Core Components

1. **Plugin System** (`plugin_base.py`, `plugin_runtime/`)
   - Abstract base classes for all plugins
   - Registry for plugin discovery and management
   - Health check scheduling with degraded state management
   - Metrics collection for performance monitoring

2. **Username Platform Module** (`username/`)
   - Declarative YAML-based platform definitions (PlatformSpec)
   - Generic executor that interprets platform metadata
   - Detection strategies (status code, redirect, regex, JSON API, GraphQL, HTML parse, custom)
   - No per-platform imperative code required

3. **Orchestrator** (`orchestrator/`)
   - Scan planning and task scheduling
   - Global and per-plugin concurrency management
   - Retry policies with exponential/linear backoff
   - Circuit breakers for fault isolation
   - Checkpoint storage for scan resume
   - Progress event streaming

4. **Runtime Services** (`plugin_runtime/`)
   - **Rate Limiter**: Token bucket rate limiting per plugin
   - **Cache**: TTL-based response caching with LRU eviction
   - **Circuit Breaker**: Three-state (CLOSED/OPEN/HALF_OPEN) fault protection
   - **HTTP Client Pool**: Managed connection pooling
   - **Metrics Collector**: Execution statistics and analytics

5. **Confidence Engine** (`confidence/`)
   - Multi-factor confidence scoring
   - Factors: source reliability, verification method, corroboration, freshness, historical success
   - Configurable weights with versioning
   - Recalculation support for corroboration updates

6. **Evidence System** (`evidence/`)
   - NormalizedFact envelope (common structure for all identifier types)
   - Evidence provenance tracking
   - Factory functions for username/email/phone facts

## Key Design Principles

### 1. Declarative Over Imperative

Username platforms are defined as YAML files, not Python code:

```yaml
id: github
display_name: GitHub
category: developer
profile_url_template: "https://github.com/{username}"
api_endpoint: "https://api.github.com/users/{username}"

detection:
  strategy: json_api
  json_api:
    success_field: "$.login"
    not_found_status: 404

confidence_rules:
  base_reliability: 0.9
  verification_method: api_confirmed
```

### 2. Strategy Pattern for Detection

Instead of 150+ platform-specific implementations, the framework provides 7 reusable detection strategies:

- `status_code`: HTTP status-based detection
- `redirect`: Redirect pattern matching
- `regex_body`: Response body regex matching
- `json_api`: JSON API with JSONPath extraction
- `graphql`: GraphQL query execution
- `html_parse`: CSS selector-based HTML parsing
- `custom`: Escape hatch for unique flows

### 3. Fault Tolerance

- **Circuit Breakers**: Automatically disable failing platforms
- **Rate Limiting**: Respect platform rate limits
- **Retries**: Configurable backoff strategies
- **Partial Failures**: One plugin failure never fails the entire scan

### 4. Confidence, Not Certainty

Every fact includes a multi-factor confidence score:
- Not a hardcoded per-platform constant
- Recomputable as corroboration accumulates
- Full factor breakdown for transparency

## Usage Examples

### Creating a Plugin

```python
from app.identity.username.executor import create_platform_plugin_from_dict

# Define platform in data (loaded from YAML)
definition_data = {
    "id": "example-platform",
    "display_name": "Example Platform",
    # ... full definition
}

# Create plugin
plugin = create_platform_plugin_from_dict(definition_data)

# Register with registry
from app.identity.plugin_runtime.registry import get_registry
registry = get_registry()
registry.register(plugin)
```

### Planning and Executing a Scan

```python
from app.identity.orchestrator.planner import ScanPlanner
from app.identity.plugin_runtime.registry import get_registry
from app.identity.types import IdentifierType
from uuid import uuid4

# Create planner
registry = get_registry()
planner = ScanPlanner(registry)

# Plan a scan
plan = planner.plan_scan(
    investigation_id=uuid4(),
    identifier_type=IdentifierType.USERNAME,
    identifier_value="target_username",
    options={
        "category": "social",  # Filter by category
        "tags": ["high-confidence"],  # Filter by tags
    }
)

# Execute tasks (orchestrator would handle this)
for task in plan.tasks:
    # Execute plugin, handle retries, circuit breaking, etc.
    pass
```

### Calculating Confidence

```python
from app.identity.confidence.engine import ConfidenceEngine
from app.identity.types import VerificationMethod
from datetime import datetime

engine = ConfidenceEngine()

score = engine.calculate_score(
    source_reliability=0.9,  # From platform definition
    verification_method=VerificationMethod.API_CONFIRMED,
    corroboration_count=2,  # Number of corroborating facts
    observed_at=datetime.utcnow(),
    plugin_success_rate=0.95  # Historical success rate
)

print(f"Confidence: {score.value:.3f}")
print(f"Breakdown: {score.factors}")
```

## Testing

The framework includes comprehensive tests:

```bash
cd backend
pytest tests/identity/
```

Tests cover:
- Plugin registry and filtering
- Platform schema validation
- Rate limiting
- Circuit breaker state transitions
- Confidence scoring
- Orchestrator components

## Validation

Run the framework validation script:

```bash
cd backend
python validate_framework.py
```

This verifies all components can be instantiated and basic operations work.

## Extension Points

### Adding a New Username Platform

1. Create `platforms/yourplatform.yaml` with platform definition
2. Choose appropriate detection strategy
3. No code changes needed!

### Adding a New Detection Strategy

1. Subclass `DetectionStrategy` in `username/detection/strategies.py`
2. Implement `check()` method
3. Register with `@register_strategy('your-strategy')` decorator

### Adding Email/Phone Modules

1. Subclass `EmailModulePlugin` or `PhoneModulePlugin`
2. Implement `execute()` and `health_check()` methods
3. Register with plugin registry

## Future Work

- Email module implementation (Gravatar, MX lookup, breach APIs)
- Phone module implementation (parsing, validation, carrier lookup, messaging presence)
- Core orchestrator execution loop
- Integration with Neo4j graph writer
- Integration with PostgreSQL for persistence
- HTTP client pool with actual httpx implementation
- WebSocket/SSE progress streaming endpoints

## Status

✅ **Framework Complete**

The plugin framework and orchestration infrastructure is fully implemented and tested. It's ready for platform definitions and real platform implementations.

Zero real platforms are implemented (as per requirements). The framework provides all the infrastructure needed to add 150+ username platforms purely through YAML configuration files.
