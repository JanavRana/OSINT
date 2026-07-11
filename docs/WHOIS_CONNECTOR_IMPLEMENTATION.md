# WHOIS Connector Implementation

**Branch:** `rudra`  
**Date:** 2026-07-11  
**Status:** Complete

## Overview

This document describes the implementation of the WHOIS connector as specified in Section 11.2 (M2 - Multi-Source Connector Framework) of MASTER_DESIGN.md.

## Implementation Details

### Files Created

1. **`backend/app/connectors/whois/__init__.py`**
   - Package initialization exposing the WhoisConnector class

2. **`backend/app/connectors/whois/connector.py`**
   - Core connector implementation subclassing BaseConnector
   - Auto-registers via `@registry.register` decorator
   - Accepts only DOMAIN identifier types
   - Uses python-whois library for lookups
   - Returns raw WHOIS data dictionary
   - 30-second timeout (WHOIS queries can be slow)

3. **`backend/app/connectors/whois/parser.py`**
   - Parser utilities for consistent WHOIS data formatting
   - Handles datetime to ISO string conversion
   - Normalizes list vs single value inconsistencies
   - Provides convenience extractors (email, dates)
   - Note: Does NOT perform M3 normalization (intentionally)

### Dependencies Added

- `python-whois==0.9.4` added to `backend/requirements.txt`

### Integration

- Updated `backend/app/connectors/__init__.py` to import WhoisConnector
- Automatic registration via decorator triggers on import
- No changes required to BaseConnector, ConnectorManager, or ConnectorRegistry

## Compliance with Requirements

### ✅ Must Requirements

- [x] Subclasses BaseConnector
- [x] Registers itself automatically via `@registry.register`
- [x] Accepts only DOMAIN identifiers (`supported_identifier_types`)
- [x] Uses Python WHOIS library (`python-whois`)
- [x] Performs WHOIS lookup
- [x] Returns RAW response (no normalization)
- [x] Does NOT normalize data (parser only formats library output)
- [x] Does NOT store data
- [x] Does NOT access database
- [x] Does NOT call FastAPI

### ✅ Architecture Compliance

- [x] Follows module boundary from Section 11.2
- [x] Isolates failures via BaseConnector.run() wrapper
- [x] Returns RawResponseEnvelope per FR3.2
- [x] Preserves provenance chain (connector name, timestamps)
- [x] Supports FR2.4 (isolated connector failure)
- [x] Respects NFR3 (adding connector requires only new module + registration)

## Usage Example

The WhoisConnector is automatically registered and available through the ConnectorManager:

```python
from app.connectors import ConnectorManager
from app.connectors.types import Identifier, IdentifierType

# Create identifier
domain = Identifier(value="example.com", type=IdentifierType.DOMAIN)

# Manager automatically resolves WHOIS connector for domain type
manager = ConnectorManager()
connectors = manager.resolve_connectors(domain)  # Returns [WhoisConnector]

# Run all applicable connectors
envelopes = await manager.run_all(domain)

# Each envelope contains:
# - connector_name: "whois"
# - status: SUCCEEDED/FAILED/TIMED_OUT
# - raw_payload: dict with WHOIS data
# - started_at, finished_at: timestamps
```

## Raw Response Structure

The connector returns the python-whois library's output as a dictionary with typical fields:

- `domain_name`: Domain name(s)
- `registrar`: Registrar name
- `creation_date`: Registration date(s)
- `expiration_date`: Expiration date(s)
- `updated_date`: Last update date(s)
- `name_servers`: List of nameservers
- `status`: Domain status codes
- `emails`: Registrant/admin/tech emails
- `name`, `org`, `address`, `city`, `state`, `zipcode`, `country`: Registrant info

Note: Structure varies by TLD and registrar. The parser.py module provides utilities to handle this variability consistently.

## Testing Notes

To test the connector:

1. Install dependencies: `pip install -r backend/requirements.txt`
2. Use ConnectorManager as shown in usage example
3. Try with various domains to see different WHOIS response formats
4. Verify timeout handling with slow/unresponsive domains
5. Verify error handling with invalid/non-existent domains

## Next Steps (Not Implemented)

The following are explicitly out of scope for this connector implementation:

- **Normalization (M3):** Converting raw WHOIS data into the shared internal schema
- **Storage (M9):** Persisting raw responses to database
- **Orchestration (M1):** Triggering connector execution based on investigation
- **Other Connectors:** RDAP, crt.sh, Wayback, GitHub, Gravatar (separate tasks)

## Design Decisions

### Why python-whois?

- Mature, well-maintained library
- Handles WHOIS protocol details internally
- Parses responses from multiple TLDs
- Synchronous API is acceptable (wrapped in BaseConnector's async framework)

### Why 30-second timeout?

- WHOIS queries can be legitimately slow (especially for some TLDs)
- Default 15s timeout from BaseConnector may be too aggressive
- 30s balances user experience with not hanging indefinitely

### Why parser.py if not normalizing?

- python-whois returns inconsistent formats (list vs single value)
- datetime objects need ISO string conversion for JSON compatibility
- Parser ensures connector always returns JSON-serializable dict
- M3 normalization still required, but has cleaner input to work with

## Conclusion

The WHOIS connector is fully implemented per MASTER_DESIGN.md specifications. It demonstrates the plugin architecture described in Section 11.2, where adding a new connector requires only:

1. Create connector module under `backend/app/connectors/<name>/`
2. Subclass BaseConnector
3. Implement fetch() method
4. Register via decorator
5. Import in `__init__.py`

No changes to framework, orchestrator, or other connectors required.
