# Intel Weave — Identity OSINT Subsystem
## Technical Architecture Document

**Status:** Design Proposal
**Scope:** Username (150+ platforms), Email, and Phone OSINT expansion
**Audience:** Engineering team implementing on top of the existing Intel Weave investigation platform

---

## 1. High-Level Architecture

The identity OSINT subsystem extends the existing pipeline:

```
Identifier → Connector → Raw Response → Normalizer → Normalized Facts → Investigation Graph → Timeline → Reports
```

Today this pipeline treats every connector as a monolithic, ad-hoc integration. At 150+ username platforms plus email and phone modules, that model breaks down: connectors become impossible to audit, rate limits collide, and partial failures cascade into full scan failures. The redesign introduces four structural changes:

1. **Declarative platform definitions** instead of imperative connector code for the username module — a platform is *data*, and a small set of generic executors interpret that data.
2. **A unified Identity Resolution Orchestrator** that sits between the existing "Connector" stage and "Raw Response" stage, responsible for scheduling, concurrency, retries, circuit breaking, and progress reporting across all three identifier types.
3. **A common Evidence/Confidence model** so username, email, and phone findings normalize into the same provenance and scoring structures already used elsewhere in the graph.
4. **A per-identifier-type module boundary** (`username/`, `email/`, `phone/`) so each domain can evolve independently while sharing the orchestration, caching, and plugin infrastructure.

### 1.1 Layered view

```
┌─────────────────────────────────────────────────────────────────────┐
│  API / Investigation Layer (FastAPI)                                │
│  - Scan lifecycle endpoints, SSE/WebSocket progress streaming        │
└─────────────────────────────────────────────────────────────────────┘
                                  │
┌─────────────────────────────────────────────────────────────────────┐
│  Identity Resolution Orchestrator                                    │
│  - Scan planning, scheduling, cancellation, resume                   │
│  - Global + per-platform concurrency governors                       │
│  - Circuit breakers, retry/backoff policy engine                     │
└─────────────────────────────────────────────────────────────────────┘
        │                       │                        │
┌───────────────┐      ┌────────────────┐      ┌──────────────────┐
│ Username       │      │ Email          │      │ Phone             │
│ Module         │      │ Module         │      │ Module            │
│ (Platform       │      │ (Verifier       │      │ (Verifier         │
│  Registry +     │      │  Registry)      │      │  Registry)        │
│  Generic         │      │                 │      │                   │
│  Executor)        │      │                 │      │                   │
└───────────────┘      └────────────────┘      └──────────────────┘
        │                       │                        │
┌─────────────────────────────────────────────────────────────────────┐
│  Plugin Runtime (shared)                                             │
│  - Registration, discovery, config, health checks, metrics           │
│  - Rate limiter, cache layer, HTTP client pool                       │
└─────────────────────────────────────────────────────────────────────┘
                                  │
┌─────────────────────────────────────────────────────────────────────┐
│  Normalization Layer                                                 │
│  - Raw Response → Normalized Fact (per identifier type)              │
└─────────────────────────────────────────────────────────────────────┘
                                  │
┌─────────────────────────────────────────────────────────────────────┐
│  Confidence Engine                                                   │
│  - Source reliability × verification method × corroboration ×        │
│    freshness × historical success → Confidence Score                 │
└─────────────────────────────────────────────────────────────────────┘
                                  │
┌─────────────────────────────────────────────────────────────────────┐
│  Graph Writer (Neo4j) + Fact Store (PostgreSQL)                      │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                        Timeline / Reports (existing)
```

Everything below "Identity Resolution Orchestrator" is new or substantially extended; everything from "Graph Writer" down reuses existing infrastructure with schema additions (Section 9).

---

## 2. Component Diagram

```
                         ┌───────────────────────────┐
                         │   Scan Request API         │
                         │ POST /scans                │
                         │ GET  /scans/{id}/stream    │
                         └────────────┬────────────────┘
                                      │
                         ┌────────────▼────────────────┐
                         │   Scan Planner               │
                         │  - resolves identifier type   │
                         │  - selects eligible platforms │
                         │  - builds ScanPlan (DAG-free,  │
                         │    flat task list)            │
                         └────────────┬────────────────┘
                                      │
                         ┌────────────▼────────────────┐
                         │   Orchestrator Core           │
                         │  - TaskQueue (priority)        │
                         │  - ConcurrencyGovernor         │
                         │  - CircuitBreakerRegistry      │
                         │  - RetryPolicyEngine           │
                         │  - CheckpointStore (resume)     │
                         └───┬───────────┬───────────┬────┘
                             │           │           │
                 ┌───────────▼──┐ ┌──────▼─────┐ ┌───▼─────────┐
                 │ Username      │ │ Email       │ │ Phone        │
                 │ Executor      │ │ Executor    │ │ Executor     │
                 │ (generic,     │ │ (module-    │ │ (module-     │
                 │  metadata-    │ │  specific   │ │  specific    │
                 │  driven)      │ │  verifiers) │ │  verifiers)  │
                 └───────┬──────┘ └──────┬─────┘ └───┬─────────┘
                         │               │            │
                 ┌───────▼───────────────▼────────────▼───────┐
                 │        Plugin Runtime Services               │
                 │  RateLimiter | CircuitBreaker | Cache        │
                 │  HTTPClientPool | MetricsCollector           │
                 │  HealthCheckScheduler                        │
                 └───────────────────────┬───────────────────────┘
                                         │
                 ┌───────────────────────▼───────────────────────┐
                 │            Normalizer Registry                  │
                 │  UsernameNormalizer | EmailNormalizer |          │
                 │  PhoneNormalizer                                 │
                 └───────────────────────┬───────────────────────┘
                                         │
                 ┌───────────────────────▼───────────────────────┐
                 │             Confidence Engine                    │
                 └───────────────────────┬───────────────────────┘
                                         │
                 ┌───────────────────────▼───────────────────────┐
                 │   Evidence Writer → PostgreSQL (facts, audit)    │
                 │   Graph Writer    → Neo4j (entities, edges)      │
                 │   Progress Publisher → WebSocket/SSE bus         │
                 └───────────────────────────────────────────────┘
```

---

## 3. Folder Structure

Proposed layout, additive to the existing repository:

```
intel-weave/
├── api/
│   └── routers/
│       └── scans.py                    # scan lifecycle endpoints (existing pattern)
│
├── identity/                            # NEW top-level module
│   ├── orchestrator/
│   │   ├── planner.py                   # builds ScanPlan from identifier + options
│   │   ├── core.py                      # TaskQueue, scheduling loop
│   │   ├── concurrency.py               # global + per-platform governors
│   │   ├── retry_policy.py
│   │   ├── circuit_breaker.py
│   │   ├── checkpoint_store.py          # resume support
│   │   └── progress_publisher.py
│   │
│   ├── plugin_runtime/
│   │   ├── registry.py                  # plugin discovery + registration
│   │   ├── loader.py                    # dynamic import / entry-point loading
│   │   ├── rate_limiter.py
│   │   ├── cache.py                     # response cache (per-plugin TTL)
│   │   ├── http_client_pool.py
│   │   ├── health_check.py
│   │   └── metrics.py
│   │
│   ├── username/
│   │   ├── executor.py                  # generic metadata-driven executor
│   │   ├── detection/
│   │   │   ├── status_code.py
│   │   │   ├── redirect.py
│   │   │   ├── regex_body.py
│   │   │   ├── json_api.py
│   │   │   ├── graphql.py
│   │   │   ├── html_parse.py
│   │   │   └── custom_logic.py          # escape hatch, still config-registered
│   │   ├── platforms/                   # declarative platform definitions
│   │   │   ├── github.yaml
│   │   │   ├── gitlab.yaml
│   │   │   ├── reddit.yaml
│   │   │   ├── x.yaml
│   │   │   ├── instagram.yaml
│   │   │   ├── tiktok.yaml
│   │   │   ├── steam.yaml
│   │   │   ├── discord.yaml
│   │   │   ├── pinterest.yaml
│   │   │   ├── medium.yaml
│   │   │   ├── linkedin.yaml
│   │   │   ├── facebook.yaml
│   │   │   ├── youtube.yaml
│   │   │   ├── twitch.yaml
│   │   │   ├── devto.yaml
│   │   │   └── ... (150+ definitions, one file each)
│   │   ├── schema/
│   │   │   └── platform_schema.py       # pydantic schema + validator for the YAML above
│   │   └── normalizer.py
│   │
│   ├── email/
│   │   ├── executor.py
│   │   ├── modules/
│   │   │   ├── gravatar.py
│   │   │   ├── avatar_discovery.py
│   │   │   ├── mx_lookup.py
│   │   │   ├── domain_analysis.py
│   │   │   ├── breach_hibp.py
│   │   │   ├── breach_generic.py        # interface for future breach APIs
│   │   │   ├── public_profiles.py
│   │   │   ├── google_workspace.py
│   │   │   ├── microsoft365.py
│   │   │   └── disposable_detection.py
│   │   └── normalizer.py
│   │
│   ├── phone/
│   │   ├── executor.py
│   │   ├── modules/
│   │   │   ├── parsing.py               # libphonenumber-backed
│   │   │   ├── validation.py
│   │   │   ├── country_detection.py
│   │   │   ├── carrier_lookup.py
│   │   │   ├── whatsapp.py
│   │   │   ├── telegram.py
│   │   │   ├── signal.py
│   │   │   └── formatting.py
│   │   └── normalizer.py
│   │
│   ├── confidence/
│   │   ├── engine.py
│   │   ├── factors.py                   # reliability, method, corroboration, freshness
│   │   └── weights_config.py            # tunable, versioned weight sets (not hardcoded)
│   │
│   ├── evidence/
│   │   ├── models.py                    # Evidence, Provenance dataclasses
│   │   └── writer.py
│   │
│   └── graph/
│       ├── entity_mapper.py             # NormalizedFact → Graph entities/edges
│       └── relationship_rules.py
│
├── db/
│   └── migrations/
│       └── versions/
│           └── xxxx_identity_osint_schema.py
│
└── config/
    └── identity/
        ├── platforms.registry.yaml      # master index of enabled platform files
        ├── concurrency.yaml
        └── confidence_weights.yaml
```

**Key design decision:** username platforms are **one YAML file per platform**, not one giant registry file. This keeps diffs small, allows per-platform code owners, and lets the platform schema validator run per-file in CI.

---

## 4. Class Hierarchy

### 4.1 Plugin abstraction

```
Plugin (ABC)
├── properties: id, display_name, category, version, enabled
├── async def health_check() -> HealthStatus
├── async def execute(context: ExecutionContext) -> RawResult
└── def describe() -> PluginMetadata

  ├── UsernamePlatformPlugin(Plugin)
  │     - wraps a single validated PlatformDefinition
  │     - delegates to a DetectionStrategy at execute-time
  │     - stateless; all behavior comes from its bound definition
  │
  ├── EmailModulePlugin(Plugin)
  │     ├── GravatarPlugin
  │     ├── AvatarDiscoveryPlugin
  │     ├── MXLookupPlugin
  │     ├── DomainAnalysisPlugin
  │     ├── HIBPBreachPlugin
  │     ├── GenericBreachAPIPlugin        # interface future vendors implement
  │     ├── PublicProfilePlugin
  │     ├── GoogleWorkspacePlugin
  │     ├── Microsoft365Plugin
  │     └── DisposableEmailPlugin
  │
  └── PhoneModulePlugin(Plugin)
        ├── PhoneParsingPlugin
        ├── PhoneValidationPlugin
        ├── CountryDetectionPlugin
        ├── CarrierLookupPlugin
        ├── WhatsAppPresencePlugin
        ├── TelegramPresencePlugin
        ├── SignalPresencePlugin
        └── PhoneFormattingPlugin
```

### 4.2 Detection strategy hierarchy (username module)

Rather than subclassing per platform (which is what produces unmaintainable 150-file connector sprawl), detection is **strategy-composed**: each `PlatformDefinition` names one strategy, and the executor dispatches to a shared, well-tested implementation.

```
DetectionStrategy (ABC)
├── async def check(username, definition, http_client) -> DetectionOutcome
│
├── StatusCodeStrategy
│     - GET profile_url; exists if status ∈ definition.success_codes
│
├── RedirectStrategy
│     - follows redirects; exists if final location matches pattern
│       (or does NOT match a "not found" redirect target)
│
├── RegexBodyStrategy
│     - exists_pattern / not_exists_pattern matched against response body
│
├── JsonApiStrategy
│     - calls definition.api_endpoint, evaluates a JSONPath-style rule
│       against the parsed body
│
├── GraphQLStrategy
│     - POSTs definition.graphql_query with variables={username},
│       evaluates response via a field-existence rule
│
├── HtmlParseStrategy
│     - CSS/XPath selector extraction, existence + optional field scraping
│       (e.g., display name, avatar) for corroboration signals
│
└── CustomLogicStrategy
      - escape hatch for platforms with genuinely unique flows
        (e.g., multi-step handshake); still registered declaratively
        with a named handler id resolved from an allow-listed registry,
        not arbitrary code injection
```

`DetectionOutcome` is the common return contract:

```
DetectionOutcome
├── exists: bool | "unknown"
├── http_status: int | None
├── evidence_fields: dict            # scraped display name, avatar url, bio, etc.
├── raw_snapshot_ref: str            # pointer to stored raw response (not embedded)
└── strategy_confidence_hint: float  # strategy-level signal, one input to Confidence Engine
```

### 4.3 Normalizer hierarchy

```
Normalizer (ABC)
├── def normalize(raw: RawResult) -> NormalizedFact

  ├── UsernameNormalizer
  ├── EmailNormalizer
  └── PhoneNormalizer
```

All three emit the same `NormalizedFact` envelope (Section 9.2) so downstream graph/confidence code is identifier-agnostic.

---

## 5. Platform Metadata Schema (Username Module)

Each platform is a single declarative file validated against a pydantic schema at load time and in CI. Example (`github.yaml`):

```yaml
id: github
display_name: GitHub
category: developer
homepage: https://github.com

profile_url_template: "https://github.com/{username}"
api_endpoint: "https://api.github.com/users/{username}"   # optional, used by json_api strategy

detection:
  strategy: json_api
  success_field: "login"          # field must exist and match {username} case-insensitively
  not_found_status: 404

network:
  timeout_seconds: 6
  retries: 2
  backoff: exponential
  base_delay_ms: 250

rate_limit:
  requests_per_minute: 30
  scope: global                   # global | per_api_key

auth:
  login_required: false
  captcha_risk: low

confidence_rules:
  base_reliability: 0.9           # official API, high trust
  verification_method: api_confirmed
  corroboration_fields: [avatar_url, name, bio, created_at]

parser:
  type: json
  fields:
    display_name: "$.name"
    avatar_url: "$.avatar_url"
    bio: "$.bio"
    account_created: "$.created_at"

normalizer: username.normalizer.default

enabled: true
tags: [tech, code-hosting, high-confidence]
```

Example for an HTML-parse platform (`pinterest.yaml`, illustrative):

```yaml
id: pinterest
display_name: Pinterest
category: social
homepage: https://pinterest.com
profile_url_template: "https://pinterest.com/{username}/"

detection:
  strategy: html_parse
  exists_selector: "meta[property='og:title']"
  not_exists_pattern: "Page not found"

network:
  timeout_seconds: 8
  retries: 1
  backoff: linear
  base_delay_ms: 500

rate_limit:
  requests_per_minute: 15
  scope: global

auth:
  login_required: false
  captcha_risk: medium

confidence_rules:
  base_reliability: 0.6           # HTML scraping is less stable than an API
  verification_method: html_scrape
  corroboration_fields: [display_name, avatar_url]

parser:
  type: html
  fields:
    display_name: "meta[property='og:title']::attr(content)"
    avatar_url: "meta[property='og:image']::attr(content)"

normalizer: username.normalizer.default
enabled: true
tags: [social, medium-confidence]
```

### 5.1 Full field reference

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | unique, kebab/lower-case, used as plugin id |
| `display_name` | string | yes | |
| `category` | enum | yes | social, developer, gaming, professional, creative, forum, other |
| `homepage` | url | yes | |
| `profile_url_template` | url template | yes | must contain `{username}` |
| `api_endpoint` | url template | no | required if strategy = json_api / graphql |
| `detection.strategy` | enum | yes | status_code, redirect, regex, json_api, graphql, html_parse, custom |
| `detection.*` | strategy-specific | yes | see Section 4.2 |
| `network.timeout_seconds` | int | yes | default 8, hard cap enforced by orchestrator |
| `network.retries` | int | yes | default 2, hard cap enforced by orchestrator |
| `network.backoff` | enum | yes | none, linear, exponential |
| `rate_limit.requests_per_minute` | int | yes | enforced by shared RateLimiter |
| `rate_limit.scope` | enum | yes | global, per_api_key |
| `auth.login_required` | bool | yes | if true, platform is excluded unless credentials configured |
| `auth.captcha_risk` | enum | yes | low, medium, high — feeds scheduling priority and UI warnings |
| `confidence_rules.base_reliability` | float 0-1 | yes | starting prior, not the final score (Section 10) |
| `confidence_rules.verification_method` | enum | yes | api_confirmed, html_scrape, redirect_inference, graphql_confirmed |
| `confidence_rules.corroboration_fields` | list[string] | no | which parsed fields count as corroboration signals |
| `parser.type` | enum | yes | json, html, text, none |
| `parser.fields` | map | no | field name → extraction path (JSONPath or CSS selector) |
| `normalizer` | string | yes | dotted path to normalizer function, resolved from allow-list |
| `enabled` | bool | yes | toggled via config or admin UI, no redeploy needed |
| `tags` | list[string] | no | used for filtering/search in scan configuration UI |

Schema validation runs at three points: (1) file save / PR CI, (2) plugin registry load at boot, (3) admin "enable platform" action — a malformed or incomplete definition can never reach the executor.

---

## 6. Plugin Lifecycle

```
┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  Discovery    │→ │  Validation   │→ │ Registration  │→ │   Idle        │
│  (scan        │   │  (schema +    │   │  (add to      │   │   (enabled,   │
│  platforms/,   │   │  duplicate-id │   │   registry,    │   │   awaiting     │
│  modules/ dirs) │   │  check)       │   │   health-check  │   │   scheduling)  │
└──────────────┘   └──────┬───────┘   │   scheduled)    │   └──────┬───────┘
                           │ fail       └──────────────┘          │
                           ▼                                       ▼
                    ┌──────────────┐                        ┌──────────────┐
                    │  Rejected     │                        │  Scheduled    │
                    │  (logged,     │                        │  (picked up   │
                    │  surfaced in  │                        │  by task       │
                    │  admin UI)    │                        │  queue)        │
                    └──────────────┘                        └──────┬───────┘
                                                                     │
                              ┌──────────────────────────────────────┼───────────────┐
                              ▼                                      ▼                ▼
                       ┌──────────────┐                      ┌──────────────┐ ┌──────────────┐
                       │  Executing    │                      │  Rate-limited │ │  Circuit-open │
                       │  (bounded by  │                      │  (queued,     │ │  (skipped,    │
                       │  concurrency  │                      │  delayed)     │ │  reported as   │
                       │  governor)    │                      └──────┬───────┘ │  degraded)     │
                       └──────┬───────┘                              │         └──────┬───────┘
                              │                                       └────────────────┘
                    ┌─────────┼──────────┐
                    ▼         ▼           ▼
             ┌──────────┐┌──────────┐┌──────────┐
             │ Success   ││ Failure   ││ Timeout   │
             │ (→ raw    ││ (→ retry  ││ (→ retry  │
             │ result)   ││ policy)   ││ policy)   │
             └──────────┘└──────────┘└──────────┘
                                          │
                                    exhausted retries
                                          ▼
                                  ┌──────────────┐
                                  │  Failed        │
                                  │  (recorded as   │
                                  │  partial-failure,│
                                  │  scan continues) │
                                  └──────────────┘
```

**Health checks** run on a schedule independent of active scans (default every 15 min for high-traffic platforms, hourly for the long tail), issuing a lightweight synthetic request (e.g., a known-good username) to detect platform-side breakage (layout change, API deprecation) *before* a real investigation hits it. A platform whose health check fails N consecutive times is automatically demoted to `degraded` and surfaced in the admin UI for maintenance, without needing to be manually disabled.

**Enable/disable** is a live config flag — the registry re-reads `platforms.registry.yaml` (or the admin-managed override table in Postgres) without requiring a redeploy. Disabling a platform mid-scan lets in-flight tasks finish but blocks new ones from being scheduled against it.

---

## 7. Execution Flow

### 7.1 Scan submission

```
1. Client → POST /scans { identifier_type, identifier_value, options }
2. Scan Planner:
     - validates identifier format (per type)
     - resolves eligible plugin set:
         username → all enabled PlatformDefinitions matching filters (category/tags)
         email    → all enabled EmailModulePlugins
         phone    → all enabled PhoneModulePlugins
     - builds a flat ScanPlan: list of ScanTask{plugin_id, identifier, priority}
     - persists ScanPlan + initial "queued" state (Postgres) → enables resume
3. Orchestrator Core enqueues all ScanTasks into the priority TaskQueue
4. Scan record returned to client with scan_id; client opens SSE/WebSocket stream
```

### 7.2 Task execution loop (per task)

```
Dequeue task
  → ConcurrencyGovernor.acquire(global_slot, platform_slot)
      (blocks if global cap or platform-specific cap is saturated)
  → CircuitBreaker.check(plugin_id)
      open  → mark task "skipped_circuit_open", release slots, publish progress
      closed/half-open → proceed
  → RateLimiter.acquire(plugin_id)
      (delays task if platform's rate budget is exhausted; does not fail it)
  → Cache.lookup(plugin_id, identifier)
      hit  → use cached RawResult (respecting TTL), skip network call
      miss → Plugin.execute(context) [network call happens here]
  → on success:
      - Cache.store(plugin_id, identifier, result)
      - CircuitBreaker.record_success(plugin_id)
      - → Normalizer → NormalizedFact
      - → Confidence Engine → scored fact
      - → Evidence Writer (Postgres) + Graph Writer (Neo4j)
      - → Checkpoint Store: mark task complete
      - → Progress Publisher: emit task-complete event
  → on failure/timeout:
      - CircuitBreaker.record_failure(plugin_id)
      - RetryPolicyEngine.should_retry(task) 
            yes → re-enqueue with backoff delay, increment attempt count
            no  → mark task "failed", record failure reason, continue scan
      - → Progress Publisher: emit task-failed event (scan is NOT aborted)
  → ConcurrencyGovernor.release(global_slot, platform_slot)
```

Crucially: **a single platform failure never fails the scan.** The scan reaches a terminal state of `completed`, `completed_with_partial_failures`, or `cancelled` — never `failed` due to one connector.

### 7.3 Cancellation

Cancellation sets `scan.status = cancelling`; the orchestrator stops dequeuing new tasks for that scan, in-flight tasks are allowed to finish (bounded by their timeout) rather than hard-killed mid-request, and the scan settles to `cancelled` once the queue for that scan is empty. Already-collected facts remain in the graph.

### 7.4 Resume

The Checkpoint Store persists, per scan, the set of `{plugin_id: status}` outcomes as they complete. Resuming a scan (deliberate resume, or automatic resume after a worker crash/restart) re-hydrates the ScanPlan, filters out tasks already in a terminal state (`success`, `failed` past max retries, `skipped`), and re-enqueues only the remainder. This makes horizontal worker scaling and process restarts safe by construction — no task is silently lost, and no completed task is re-run.

### 7.5 Streaming progress

Progress events (`task_started`, `task_complete`, `task_failed`, `task_skipped`, `scan_complete`) are published to a lightweight pub/sub channel (Redis Streams or Postgres LISTEN/NOTIFY, depending on existing infra choices) keyed by `scan_id`, and relayed to the client over the existing SSE/WebSocket transport. This lets the frontend render a live 150-platform progress grid without polling.

---

## 8. Graph Integration

### 8.1 Principle: avoid star graphs

A naive design puts a `Person` node at the center with 150+ direct `HAS_ACCOUNT` edges to platform nodes. This is technically a graph but analytically flat — it doesn't capture that a GitHub account and a personal domain corroborate each other independently of the Person node, or that an email's Gravatar hash matches an avatar reused across three platforms.

Instead, the graph models identifiers as first-class intermediate entities, and evidence as edges with properties (not just presence/absence):

```
(Person)-[:USES_IDENTIFIER]->(Username {value:"jdoe"})
(Username)-[:VERIFIED_ON {confidence:0.91, method:"api_confirmed"}]->(SocialAccount:GitHub)
(Username)-[:VERIFIED_ON {confidence:0.62, method:"html_scrape"}]->(SocialAccount:Pinterest)

(Person)-[:USES_IDENTIFIER]->(Email {value:"j@example.com"})
(Email)-[:HAS_MX]->(Website{domain:"example.com"})
(Email)-[:RESOLVES_TO]->(GravatarProfile)
(Email)-[:APPEARED_IN]->(BreachEvent {source:"HIBP", date:"2019-03-01"})

(Person)-[:USES_IDENTIFIER]->(Phone {value:"+1..."})
(Phone)-[:REGISTERED_ON]->(SocialAccount:WhatsApp)
(Phone)-[:REGISTERED_ON]->(SocialAccount:Telegram)

(SocialAccount:GitHub)-[:SHARES_AVATAR_WITH {similarity:0.97}]->(GravatarProfile)
(SocialAccount:Pinterest)-[:SHARES_DISPLAY_NAME_WITH]->(SocialAccount:Instagram)
```

Cross-links like `SHARES_AVATAR_WITH` and `SHARES_DISPLAY_NAME_WITH` are what make the graph valuable for corroboration — they're computed by a post-processing **Corroboration Pass** that runs after a batch of facts lands, comparing `evidence_fields` (avatar hashes, display names, bios, creation dates) across newly-written `SocialAccount` nodes for the same investigation.

### 8.2 Entity mapping rules

| NormalizedFact type | Graph entity created/matched | Key edges |
|---|---|---|
| Username → platform hit | `SocialAccount` (labeled by platform) | `Username -[:VERIFIED_ON]-> SocialAccount` |
| Email → Gravatar match | `GravatarProfile` | `Email -[:RESOLVES_TO]-> GravatarProfile` |
| Email → MX/domain | `Website`/`Organization` | `Email -[:HAS_MX]-> Website` |
| Email → breach hit | `BreachEvent` | `Email -[:APPEARED_IN]-> BreachEvent` |
| Phone → messaging presence | `SocialAccount` (labeled by app) | `Phone -[:REGISTERED_ON]-> SocialAccount` |
| Phone → carrier | `Carrier` | `Phone -[:SERVICED_BY]-> Carrier` |
| Cross-fact corroboration | (no new entity) | `SocialAccount -[:SHARES_*_WITH {similarity}]-> SocialAccount` |

All edges carry `confidence`, `verification_method`, `evidence_id` (FK to Postgres Evidence row), and `observed_at` properties, so the graph itself is queryable for "show me only high-confidence links" without a round-trip to Postgres.

---

## 9. Database Schema Additions

### 9.1 New PostgreSQL tables

```
platform_definitions
  id                    text primary key        -- matches YAML `id`
  display_name          text
  category              text
  config_snapshot        jsonb                    -- full validated definition, versioned
  enabled                boolean
  health_status           text                     -- healthy | degraded | unknown
  last_health_check_at    timestamptz
  created_at, updated_at

scans
  id                    uuid primary key
  investigation_id       uuid references investigations(id)
  identifier_type         text                     -- username | email | phone
  identifier_value        text
  status                 text                     -- queued|running|completed|
                                                     -- completed_with_partial_failures|
                                                     -- cancelling|cancelled|failed
  options                jsonb                    -- filters, tags, concurrency overrides
  created_at, started_at, completed_at

scan_tasks
  id                    uuid primary key
  scan_id                 uuid references scans(id)
  plugin_id               text
  status                 text                     -- queued|running|success|failed|
                                                     -- skipped_circuit_open|skipped_disabled|
                                                     -- cancelled
  attempt_count            int
  last_error               text
  raw_result_ref            text                     -- pointer to stored raw response (blob store)
  started_at, completed_at

evidence
  id                    uuid primary key
  scan_task_id             uuid references scan_tasks(id)
  fact_id                 uuid references normalized_facts(id)
  source_plugin_id          text
  verification_method       text
  raw_snapshot_ref           text
  observed_at               timestamptz
  created_at

normalized_facts
  id                    uuid primary key
  investigation_id       uuid references investigations(id)
  identifier_type         text
  identifier_value        text
  fact_type               text                     -- e.g. platform_account, mx_record,
                                                     -- breach_membership, carrier_match
  fact_payload             jsonb
  confidence_score          numeric(4,3)
  confidence_breakdown      jsonb                    -- factor-by-factor detail (Section 10)
  graph_entity_ref           text                     -- Neo4j node id, once written
  created_at

circuit_breaker_state
  plugin_id               text primary key
  state                  text                     -- closed|open|half_open
  failure_count            int
  opened_at                timestamptz
  next_probe_at             timestamptz

plugin_metrics_rollup       -- periodic rollup, feeds "historical_success" confidence factor
  plugin_id               text
  window_start, window_end   timestamptz
  attempts, successes, failures, avg_latency_ms
```

### 9.2 `NormalizedFact` envelope (shared across identifier types)

```
NormalizedFact
├── id
├── investigation_id
├── identifier_type: username | email | phone
├── identifier_value
├── fact_type: string                 # platform_account, mx_record, breach_membership, ...
├── fact_payload: dict                # type-specific structured data
├── evidence: Evidence                # provenance, see below
└── confidence: ConfidenceScore

Evidence
├── source_plugin_id
├── verification_method
├── raw_snapshot_ref                  # never inline the full raw response in the fact
└── observed_at

ConfidenceScore
├── value: float [0,1]
└── breakdown: { reliability, method, corroboration, freshness, historical_success }
```

### 9.3 Neo4j additions

New node labels: `SocialAccount`, `GravatarProfile`, `BreachEvent`, `Carrier`. New relationship types: `VERIFIED_ON`, `RESOLVES_TO`, `HAS_MX`, `APPEARED_IN`, `REGISTERED_ON`, `SERVICED_BY`, `SHARES_AVATAR_WITH`, `SHARES_DISPLAY_NAME_WITH`. All carry the `confidence` / `verification_method` / `evidence_id` / `observed_at` properties described in 8.2.

---

## 10. Confidence Engine

Confidence is never a hardcoded per-platform constant. It's computed at fact-creation time (and recomputable later, as corroboration accumulates) from five weighted factors:

```
confidence = clamp(
    w1 * source_reliability
  + w2 * verification_method_score
  + w3 * corroboration_score
  + w4 * freshness_score
  + w5 * historical_success_score
, 0, 1)
```

| Factor | Source | Notes |
|---|---|---|
| `source_reliability` | `platform_definitions.config_snapshot.confidence_rules.base_reliability` | The declarative prior from the platform definition — a starting point, not the output |
| `verification_method_score` | lookup table keyed by `verification_method` | e.g. `api_confirmed`→0.95, `graphql_confirmed`→0.9, `redirect_inference`→0.5, `html_scrape`→0.6 — table is config, not code |
| `corroboration_score` | computed by the Corroboration Pass (Section 8.1) | increases when independent facts agree (matching avatar hash, matching display name across unrelated platforms, matching creation-date clustering); a single-source fact is capped below full confidence regardless of source reliability |
| `freshness_score` | `now() - observed_at`, decayed per identifier_type | username existence decays slowly; breach data and carrier data decay differently; decay curve is configurable per `fact_type` |
| `historical_success_score` | `plugin_metrics_rollup` | a platform whose past results have been frequently corrected/disputed in this deployment gets down-weighted over time |

Weights `w1..w5` live in `config/identity/confidence_weights.yaml`, versioned, and every `ConfidenceScore.breakdown` records which weight-set version produced it — so historical scores remain reproducible even as weights are tuned. Analysts can see the full factor breakdown in the UI (not just a final number), which matters for investigative defensibility.

Recomputation trigger: whenever a new corroborating fact lands for the same identifier within an investigation, affected facts' `corroboration_score` (and therefore overall confidence) are recalculated asynchronously — confidence is a living value, not a write-once field.

---

## 11. Performance Strategy

| Concern | Approach |
|---|---|
| 150+ concurrent platforms | Fully async I/O (single event loop per worker, `httpx`-style async client pool); no per-platform thread |
| Global concurrency | `ConcurrencyGovernor` enforces a configurable global in-flight cap (e.g. 200) independent of platform count |
| Per-platform concurrency | Each `PlatformDefinition`/module plugin gets its own semaphore sized by `rate_limit.requests_per_minute`, preventing one platform's slowness from starving others |
| Batching | Scan Planner chunks ScanPlans; for very large batch investigations (e.g. bulk username lists), tasks are grouped so cache warm-up and connection reuse are maximized per platform |
| Streaming progress | Pub/sub progress events (Section 7.5) mean the client never blocks on full-scan completion to render results |
| Cancellation | Cooperative — governed by checking `scan.status` at each loop iteration, not forced task termination, so partial state stays consistent |
| Resume | Checkpoint Store + idempotent task keys (`scan_id + plugin_id`) make replays safe |
| Horizontal scaling | Orchestrator Core is stateless per-process; TaskQueue and CheckpointStore live in shared infra (Redis/Postgres), so multiple worker processes/pods can pull from the same queue. Circuit breaker and rate-limiter state must be shared (Redis-backed), not per-process, or multiple workers will collectively exceed a platform's real rate limit |
| Caching | Per-plugin response cache with a TTL tuned by `fact_type` volatility (e.g. username existence cached hours, breach data cached longer, live presence like WhatsApp cached briefer) — cuts redundant load on external services across repeated/overlapping investigations |
| Circuit breaking | Prevents wasting concurrency budget hammering a platform that's currently down or blocking the deployment's IP range |

---

## 12. Migration Strategy

The rollout is staged to avoid disrupting the existing five-identifier pipeline:

**Phase 1 — Foundation (no user-facing change)**
Add the `identity/` module skeleton, plugin runtime, orchestrator, and new DB tables alongside the existing connector system. Existing Domain/Email/Username/Phone/Wallet/IP connectors keep running unchanged.

**Phase 2 — Username module cutover**
Port the existing username connector logic behind the new `UsernamePlatformPlugin` abstraction, expressed as YAML platform definitions for the current supported set (GitHub, GitLab, Reddit, X, Instagram, TikTok, Steam, Discord, Pinterest, Medium, LinkedIn, Facebook, YouTube, Twitch, Dev.to). Validate parity against the old pipeline (same identifiers in, same or better facts out) before removing the legacy path. Feature-flag the new executor so it can be toggled per-investigation during validation.

**Phase 3 — Scale out username platforms**
Add remaining platforms toward 150+, in batches by category, each batch going through: schema validation → staging health check → confidence-rule review → enabled in production. This is the phase most parallelizable across contributors, since each platform file is independent.

**Phase 4 — Email module build-out**
Introduce email verifier plugins (Gravatar, MX/domain analysis, disposable detection first — no external creds required), then breach APIs (HIBP), then OAuth-gated modules (Google Workspace, Microsoft 365) once credential management is in place.

**Phase 5 — Phone module build-out**
Parsing/validation/formatting first (libphonenumber-backed, no external calls), then carrier lookup, then messaging-presence checks (WhatsApp, Telegram, Signal), each gated by ToS/compliance review before enabling in production.

**Phase 6 — Legacy connector retirement**
Once parity is confirmed and the new pipeline has run in production for a full investigation cycle, retire the old ad-hoc connector code paths for username/email/phone, leaving Domain/Wallet/IP on the existing architecture (out of scope for this document) or migrating them later using the same plugin pattern.

Each phase ships independently deployable, backward-compatible changes — at no point does an in-progress migration block existing investigations from running.

---

## 13. Future Extensibility

- **New identifier types** (e.g., IP-adjacent identity signals, cryptocurrency addresses tied to identity) reuse the same `Plugin` → `Normalizer` → `NormalizedFact` → `Confidence Engine` → `Graph Writer` pipeline; only a new module directory and entity-mapping rules are needed.
- **New username platforms** are pure config additions (a YAML file + PR), not code changes, unless they require a genuinely new detection strategy — in which case exactly one new `DetectionStrategy` implementation serves all future platforms needing that pattern.
- **Commercial data-enrichment vendors** (breach APIs, carrier APIs, identity-resolution APIs) plug in via the `GenericBreachAPIPlugin`-style interfaces already defined in Section 4.1, keeping vendor-specific auth/quirks isolated from the orchestrator.
- **Confidence tuning** is a config change (weights YAML + method-score table), auditable and reversible, without a code deploy.
- **Per-investigation platform selection profiles** (e.g., "fast scan: top 20 platforms" vs "deep scan: all 150+") are just saved filter sets over `tags`/`category` in the platform registry — no orchestrator changes required.
- **Multi-tenant rate-limit isolation**, if Intel Weave later serves multiple customer organizations from shared infrastructure, is a natural extension of `rate_limit.scope` (`global` → `per_tenant`) without restructuring the governor.

---

## Appendix A — Compliance Note

Every module in this design (username presence checks, public breach-notification lookups, MX/domain analysis, carrier/messaging-presence checks) is scoped to querying publicly accessible endpoints or opt-in commercial APIs, never to bypassing authentication, defeating CAPTCHAs, or accessing non-public data stores. `captcha_risk` is modeled as a scheduling/UI signal (to warn operators and throttle politely) rather than as something the system attempts to defeat. Modules gated by provider Terms of Service (e.g., messaging-presence checks) are flagged in Phase 5 for explicit compliance review before production enablement, and the plugin's `auth.login_required` / `captcha_risk` fields exist precisely so engineering and legal can jointly gate which platforms are eligible to ship.







