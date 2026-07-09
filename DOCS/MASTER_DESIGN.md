# MASTER_DESIGN.md
## Advanced Multi-Platform OSINT Intelligence Aggregator

**Document status:** Single source of truth for all development work on this project.
**Audience:** Any human or AI model (Claude, ChatGPT, Gemini, etc.) contributing code, design, or review.
**Rule for all contributors:** Read this document in full before writing any code. If a coding task conflicts with this document, this document wins. If this document is silent on something, prefer the simplest option consistent with the principles in Section 3 (Goals) and Section 8 (Non-Functional Requirements).

---

## Table of Contents

1. Project Vision
2. Problem Statement
3. Goals
4. Scope
5. Users
6. User Journey
7. Functional Requirements
8. Non-Functional Requirements
9. High-Level Architecture
10. Module Breakdown
11. Detailed Description of Every Module
12. Data Flow
13. Folder Structure (High Level Only)
14. Database Overview (Not Full Schema)
15. API Overview (Major Endpoints Only)
16. Frontend Overview
17. Backend Overview
18. Technology Decisions
19. Future Expansion
20. Development Roadmap

---

## 1. Project Vision

The Advanced Multi-Platform OSINT Intelligence Aggregator (from here on, "the Platform") is a web application that lets a cybercrime investigator start from a single fragment of information — an email address, a phone number, a username, a domain, a cryptocurrency wallet address, or an image — and end with a structured, evidence-backed picture of the entity behind it.

Today, an investigator does this manually: opening a dozen browser tabs (WHOIS lookup, crt.sh, Wayback Machine, GitHub search, Gravatar hash lookup, etc.), copying results into a notes document, mentally cross-referencing which results belong to the same person or organization, and finally writing up findings into a report. This is slow, error-prone, hard to reproduce, and hard to hand off to another investigator.

The Platform's vision is to compress that manual process into a single guided workflow:

1. Investigator submits one or more identifiers.
2. The Platform queries every relevant OSINT source automatically.
3. Results are normalized into one common shape regardless of source.
4. Matching results are correlated into unified entities with confidence scores.
5. The investigator explores the results visually as a graph and as a profile.
6. The investigator exports a professional PDF report suitable for a case file.

The Platform is explicitly a **foundation**, not a finished product. It is built to be extended by future AI-assisted features (Section 19) without requiring architectural rewrites. Every module in this document is designed with a "day one" scope that is intentionally small, and an "extensibility" note that describes how it grows later without needing to change its shape.

This document deliberately avoids enterprise-scale patterns (microservices, message queues, container orchestration, distributed databases). The Platform must be buildable and demoable within a hackathon timeframe by a small team (or a single developer working with AI assistance), while still being a credible foundation for a real product afterward.

---

## 2. Problem Statement

Cybercrime and fraud investigators frequently need to answer a version of the same question: **"Who or what is behind this identifier, and what else is connected to it?"**

Today this requires:

- Knowing which OSINT sources are useful for which identifier types (a phone number and a domain need completely different lookups).
- Manually running each lookup, one at a time, in different tools or websites.
- Manually reading through inconsistent output formats (HTML pages, JSON blobs, plain text WHOIS records) and extracting the useful facts.
- Manually deciding, with no tooling support, whether two pieces of evidence describe the same real-world entity (e.g., "is this GitHub account and this email the same person?").
- Manually building a timeline of events (domain registration date, certificate issuance date, archive snapshot dates) by reading through raw records.
- Manually assembling a write-up for a case file, often just by pasting screenshots and links into a document.

This is slow, inconsistent between investigators, difficult to audit, and does not scale as the number of identifiers and sources involved in a single case grows. There is no lightweight, self-hostable tool that treats "aggregate, normalize, correlate, visualize, report" as one connected pipeline rather than five disconnected steps performed by hand.

The Platform exists to close that gap for the first version, using only deterministic, explainable logic (no opaque machine learning), so that every conclusion the Platform reaches can be traced back to the evidence and the rule that produced it — a hard requirement for anything intended to support an investigation.

---

## 3. Goals

**Primary goals for this version:**

- G1. Accept one or more identifiers of the supported types (email, phone, username, domain, wallet address, image) as investigation input.
- G2. Automatically determine and run the OSINT connectors relevant to each identifier type.
- G3. Normalize all connector output into one internal schema so the rest of the system never needs to know which source produced a fact.
- G4. Deterministically correlate normalized facts into unified entities with a visible, explainable confidence score.
- G5. Visualize entities and relationships as an interactive graph.
- G6. Present a single consolidated "Unified Identity Profile" view per entity.
- G7. Reconstruct a chronological timeline of dated events discovered during investigation.
- G8. Export a professional, self-contained PDF report per investigation.
- G9. Make adding a new OSINT connector a small, well-defined, isolated task (a strong plugin boundary), so both humans and AI models can add new sources without touching unrelated code.

**Explicit non-goals for this version** (see Section 19 for why these are deferred, not rejected):

- Machine-learning-based entity matching.
- Natural language query interface.
- Continuous / scheduled monitoring of identifiers.
- Multi-user workspaces, roles, or permissions beyond a single investigator session.
- Real-time collaborative editing of an investigation.
- High-availability, horizontal scaling, or multi-region deployment.

**Guiding engineering principle:** at every design decision in this document, prefer the option that is simpler to build, simpler to explain, and simpler for another AI model to safely extend — even if it is less "impressive" architecturally. Complexity is a cost, not a feature.

---

## 4. Scope

### 4.1 In Scope (v1)

- Single-investigator, single-session web application (no multi-tenant auth system required for v1; a minimal login/API-key gate is acceptable, see Section 8).
- Six identifier input types: email, phone number, username, domain, cryptocurrency wallet address, image (for hash/metadata lookups such as Gravatar — not reverse image search, which is deferred).
- Six example connectors: WHOIS, RDAP, crt.sh, Wayback Machine, GitHub, Gravatar. The connector framework must support more than six, but only these six ship in v1.
- One internal normalized data schema shared by all connectors.
- Deterministic, rule-based entity correlation (string/hash matching, shared-attribute matching, confidence scoring via fixed rules — no ML).
- Interactive relationship graph (Cytoscape.js) with clickable nodes showing evidence.
- Unified Identity Profile view.
- Investigation Timeline view.
- PDF report generation (ReportLab) containing summary, profile, graph snapshot, timeline, evidence, sources, and confidence scores.

### 4.2 Out of Scope (v1)

- Any feature listed in Section 19 (Future Expansion).
- Any connector beyond the six listed above (the framework must support them; v1 does not ship them).
- Distributed processing, background job clusters, or microservices.
- Mobile applications.
- Any capability for locating a specific living person's real-time whereabouts. The Platform deals only in historical, publicly indexed OSINT records.

### 4.3 Responsible-Use Boundary

The Platform is a defensive/investigative tool intended for legitimate fraud, abuse, and cybercrime investigation work, built entirely on top of publicly accessible data sources that already provide public lookup interfaces (WHOIS/RDAP registries, certificate transparency logs, the Internet Archive, GitHub's public API, Gravatar's public hash lookup). It does not access private, paywalled, authenticated, or breached data sources, and v1 explicitly excludes any "breach database" connector. Any future connector proposal should be checked against this boundary before being added to the framework.

---

## 5. Users

| User | Description | Primary Need |
|---|---|---|
| Cybercrime Investigator | Front-line user. Runs investigations, reviews graph/profile/timeline, exports reports. | Fast, trustworthy aggregation and correlation of public evidence. |
| Investigation Lead / Reviewer | Reviews a completed investigation and its PDF report, possibly for use in a case file or handoff. | A clear, evidence-linked report they can trust without re-doing the work. |
| Platform Developer (human or AI) | Extends the Platform — new connectors, new views, future AI features. | A predictable, modular codebase and a single authoritative design reference (this document). |

v1 does not need to distinguish these users with different permissions — they are described here to keep design decisions (e.g., report format, evidence traceability) anchored to real needs rather than abstract requirements.

---

## 6. User Journey

1. **Start an investigation.** Investigator opens the Platform and creates a new investigation, giving it a name (e.g., "Case 2026-0417").
2. **Submit identifiers.** Investigator enters one or more identifiers (e.g., an email and a domain believed to be related). Each identifier is tagged with its type, either auto-detected or manually selected.
3. **Orchestration runs.** The Search Orchestrator determines which connectors apply to each identifier and dispatches them. The UI shows per-connector progress (queued / running / done / failed).
4. **Raw results arrive and are normalized.** As each connector finishes, its raw output is normalized into the internal schema and stored against the investigation.
5. **Correlation runs.** The Entity Correlation Engine compares normalized facts, merges duplicates, and produces unified entities with confidence scores and relationship edges.
6. **Investigator explores results.**
   - Graph view: interactive node/edge visualization; clicking a node reveals its evidence and source list.
   - Profile view: consolidated identity profile per unified entity.
   - Timeline view: chronological list of all dated events discovered.
7. **Investigator refines (optional).** Investigator can add another identifier discovered during exploration (e.g., a username found via GitHub) and re-run orchestration for it, growing the same investigation incrementally.
8. **Investigator exports report.** Investigator triggers PDF report generation. The Platform renders a report with a summary, the unified profile(s), a graph snapshot image, the timeline, and a full evidence/source appendix with confidence scores.
9. **Investigation is saved.** The full investigation (inputs, raw results, normalized facts, correlated entities, generated report) persists in the database and can be reopened later.

---

## 7. Functional Requirements

### 7.1 Identifier Input
- FR1.1 The system shall accept identifiers of type: email, phone, username, domain, wallet address, image.
- FR1.2 The system shall auto-detect identifier type where feasible (e.g., regex for email/domain/phone) and allow manual override.
- FR1.3 The system shall allow multiple identifiers to belong to the same investigation.
- FR1.4 The system shall allow adding identifiers to an existing investigation after initial creation.

### 7.2 Orchestration
- FR2.1 The system shall maintain a mapping of identifier type → applicable connectors.
- FR2.2 The system shall dispatch all applicable connectors for a given identifier without requiring the investigator to select connectors manually (manual override/opt-out is allowed but not required).
- FR2.3 The system shall track and expose the status of each connector execution (queued, running, succeeded, failed, timed out).
- FR2.4 The system shall isolate a single connector failure so it does not block or fail other connectors in the same investigation.

### 7.3 Normalization
- FR3.1 The system shall convert every connector's raw response into the shared internal schema (Section 11.3) before storage.
- FR3.2 The system shall retain the original raw connector response alongside the normalized version, for evidence and debugging purposes.
- FR3.3 The system shall record, for every normalized fact, which connector and which raw response produced it.

### 7.4 Correlation
- FR4.1 The system shall compare normalized facts across all connector results within an investigation to find matching or related attributes (e.g., same email appearing via two different connectors).
- FR4.2 The system shall merge matching facts into a single unified entity.
- FR4.3 The system shall assign every unified entity, and every relationship edge between entities, a confidence score derived from fixed, documented rules.
- FR4.4 The system shall make the reasoning behind a confidence score inspectable (i.e., which rule fired, based on which evidence).
- FR4.5 Correlation shall be deterministic: running it twice on the same data shall produce the same result.

### 7.5 Graph Visualization
- FR5.1 The system shall render unified entities as nodes and relationships as edges in an interactive graph.
- FR5.2 The system shall allow clicking a node to view its evidence (source connectors, raw facts, confidence score, timestamps).
- FR5.3 The system shall allow clicking an edge to view the relationship type and the evidence that produced it.
- FR5.4 The system shall support basic graph interactions: pan, zoom, drag nodes, expand/collapse clusters.

### 7.6 Unified Identity Profile
- FR6.1 The system shall present, per unified entity, a consolidated profile listing associated emails, phones, usernames, domains, social accounts, confidence, evidence, and sources.
- FR6.2 The system shall allow navigating from a profile entry directly to its supporting evidence.

### 7.7 Timeline
- FR7.1 The system shall extract dated events from normalized facts (e.g., domain registration date, certificate issuance date, archive snapshot date).
- FR7.2 The system shall render these events in chronological order.
- FR7.3 The system shall allow filtering the timeline by entity or by event type.

### 7.8 Reporting
- FR8.1 The system shall generate a PDF report per investigation containing: executive summary, unified profile(s), a graph snapshot image, the timeline, an evidence appendix, a source list, and confidence scores.
- FR8.2 The generated report shall be downloadable and shall not require the Platform to remain online to be viewed afterward (it is a self-contained PDF file).
- FR8.3 The system shall regenerate the report on demand to reflect the latest state of an investigation.

### 7.9 Persistence
- FR9.1 The system shall persist investigations, identifiers, raw connector results, normalized facts, unified entities, relationships, and generated reports.
- FR9.2 The system shall allow reopening a previously created investigation.

---

## 8. Non-Functional Requirements

- NFR1. **Simplicity first.** The system shall favor a single deployable backend service and a single frontend application over any distributed or microservice topology.
- NFR2. **Modularity.** Each module described in Section 11 shall be implementable and testable in isolation, with a clearly defined interface to the rest of the system.
- NFR3. **Extensibility.** Adding a new connector shall require writing one new connector module conforming to the connector interface, plus a registry entry — no changes to the orchestrator, normalization engine, or correlation engine.
- NFR4. **Explainability.** Every automated conclusion (a merged entity, a confidence score, a timeline event) must be traceable back to the specific raw evidence and rule that produced it. No "black box" scoring.
- NFR5. **Resilience to partial failure.** A failing or slow connector shall not block the rest of an investigation from completing.
- NFR6. **Reasonable performance for a hackathon demo.** A typical investigation (1–3 identifiers, six connectors) should complete orchestration in well under a minute under normal network conditions. This is a soft target, not a hard SLA.
- NFR7. **Data integrity over data volume.** It is more important that stored facts are accurately linked to their evidence than that the system store the maximum possible amount of data.
- NFR8. **Local-first / self-hostable.** The system shall run on a single machine (or a small number of containers via simple docker-compose) without requiring cloud-managed distributed infrastructure.
- NFR9. **Auditability.** The system shall retain raw connector responses so that any normalized fact or correlation decision can be independently verified after the fact.
- NFR10. **Reasonable security hygiene.** Secrets (API keys/tokens for connectors that need them) shall be stored in environment configuration, never hard-coded or committed. A minimal authentication gate shall protect the application from being used as an open public tool.

---

## 9. High-Level Architecture

The Platform is a classic three-tier web application, deliberately monolithic at the backend level, with an internal modular structure that mimics plugin/service boundaries without paying for actual service-separation costs.

```
                        ┌─────────────────────────────┐
                        │        React + TS SPA        │
                        │  (Frontend Overview, Sec.16) │
                        └───────────────┬──────────────┘
                                        │ REST (JSON) over HTTPS
                        ┌───────────────▼──────────────┐
                        │        FastAPI Backend        │
                        │  ┌─────────────────────────┐  │
                        │  │   Search Orchestrator    │  │
                        │  └────────────┬─────────────┘  │
                        │               │                │
                        │  ┌────────────▼─────────────┐  │
                        │  │  Connector Framework      │  │
                        │  │  (WHOIS, RDAP, crt.sh,    │  │
                        │  │   Wayback, GitHub,        │  │
                        │  │   Gravatar, ...)          │  │
                        │  └────────────┬─────────────┘  │
                        │               │ raw responses   │
                        │  ┌────────────▼─────────────┐  │
                        │  │  Normalization Engine     │  │
                        │  └────────────┬─────────────┘  │
                        │               │ normalized facts│
                        │  ┌────────────▼─────────────┐  │
                        │  │  Entity Correlation Engine│  │
                        │  └────────────┬─────────────┘  │
                        │               │ unified entities│
                        │               │ + relationships │
                        │  ┌────────────▼─────────────┐  │
                        │  │  Report Generation Service│  │
                        │  └───────────────────────────┘  │
                        └───────┬───────────────┬─────────┘
                                │               │
                    ┌───────────▼───┐   ┌───────▼────────┐
                    │  PostgreSQL    │   │     Neo4j       │
                    │ (investigations,│  │ (entities and   │
                    │  raw & normal- │   │  relationships  │
                    │  ized data,    │   │  for graph      │
                    │  reports)      │   │  queries/viz)   │
                    └────────────────┘   └─────────────────┘
```

**Architectural style:** modular monolith. One backend process, internally divided into clearly bounded modules (Section 11) communicating through plain Python function/service calls, not network calls. This keeps the system hackathon-buildable while the module boundaries keep it AI-extensible and future-proof for splitting out services later if ever truly needed (see Section 19 — this document deliberately does not design that split now).

**Why two databases (PostgreSQL + Neo4j):** PostgreSQL is the system of record for everything (investigations, raw results, normalized facts, reports) because it is simple, transactional, and well understood. Neo4j is used only for the parts of the system that are naturally graph-shaped — the unified entities and relationships that power the interactive graph view — because expressing "find everything connected to this entity within two hops" in a relational database is unnecessarily painful, while it is a single native query in a graph database. Neo4j is a read/query convenience layer for the graph view; PostgreSQL remains the source of truth (see Section 14).

---

## 10. Module Breakdown

| # | Module | One-line Purpose |
|---|---|---|
| M1 | Search Orchestrator | Accepts identifiers, determines applicable connectors, coordinates execution, tracks status. |
| M2 | Multi-Source Connector Framework | Plugin-style interface + registry for OSINT source connectors; ships WHOIS, RDAP, crt.sh, Wayback Machine, GitHub, Gravatar. |
| M3 | Data Normalization Engine | Converts every connector's raw output into the shared internal schema. |
| M4 | Entity Correlation Engine | Deterministically merges normalized facts into unified entities and scored relationships. |
| M5 | Interactive Relationship Graph | Frontend + supporting API for visualizing entities/relationships and inspecting evidence. |
| M6 | Unified Identity Profile | Frontend + supporting API for the consolidated per-entity profile view. |
| M7 | Investigation Timeline | Extracts and renders dated events chronologically. |
| M8 | PDF Investigation Report | Generates the final downloadable report from all of the above. |
| M9 | Investigation & Persistence Layer | Cross-cutting: owns the concept of an "investigation" and persists all state (supports M1–M8, not user-facing on its own). |

M9 is not one of the eight product-facing features from the prompt, but it is called out explicitly here because every other module depends on it, and giving it a clear boundary now prevents "investigation state" logic from leaking into every other module ad hoc.

---

## 11. Detailed Description of Every Module

Each module below follows the same template: **Purpose, Responsibilities, Inputs, Outputs, Dependencies, Future Extensibility.**

### 11.1 M1 — Search Orchestrator

**Purpose:** Single entry point that turns "an investigator submitted these identifiers" into "these connectors ran, and here is what happened."

**Responsibilities:**
- Accept a batch of identifiers (with type, either given or auto-detected) for a specific investigation.
- Look up, per identifier type, the list of registered connectors that apply (via the Connector Framework's registry, M2).
- Dispatch each applicable connector for each identifier.
- Track per-connector-per-identifier execution status (queued, running, succeeded, failed, timed out).
- Enforce a per-connector timeout so one slow external source cannot stall the investigation.
- Hand every successful raw connector response to the Normalization Engine (M3).
- Aggregate status so the frontend can show live progress.

**Inputs:**
- Investigation ID.
- List of identifiers (value + type).

**Outputs:**
- Per-connector execution records (status, timing, raw response reference or error) persisted via M9.
- A trigger/event that normalized data is ready, which downstream (M3, then M4) consumes.

**Dependencies:** M2 (Connector Framework, to know what to run and to actually run it), M9 (Investigation & Persistence Layer, to record status and identifiers), M3 (Normalization Engine, as the consumer of its output).

**Future Extensibility:** In v1, orchestration runs connectors concurrently within a single backend process (e.g., an async task group) and is synchronous from the API's point of view (poll for status). This module's interface is written so that swapping "run concurrently in-process" for "enqueue onto a background task queue" (a Future Expansion concern, see Section 19) requires no change to its public interface — only to its internal execution strategy.

---

### 11.2 M2 — Multi-Source Connector Framework

**Purpose:** Provide one consistent way to add, register, and execute an OSINT data source, so that adding source #7 is a small, isolated task.

**Responsibilities:**
- Define a single connector interface that every source implements: given an identifier (value + type), return a raw result or a clearly-typed error/timeout.
- Maintain a registry mapping identifier type → list of connectors that can handle it (e.g., `domain` → [WHOIS, RDAP, crt.sh, Wayback Machine]; `username` → [GitHub]; `email` → [Gravatar]).
- Provide shared plumbing every connector needs: HTTP client with sane timeout/retry defaults, rate-limit backoff, structured error wrapping.
- Ship six reference connectors in v1: **WHOIS**, **RDAP**, **crt.sh** (certificate transparency search), **Wayback Machine** (archive snapshot lookup), **GitHub** (public profile/repo search by username or associated email), **Gravatar** (public hash-based avatar/profile lookup by email).
- Ensure each connector's raw response is returned in a self-describing envelope (source name, timestamp, success/failure, raw payload) so M3 can process it uniformly.

**Inputs:** Identifier (value + type) from M1.

**Outputs:** Raw response envelope (per connector, per identifier) to M1/M3.

**Dependencies:** None internal beyond shared HTTP plumbing (this is intentionally the most decoupled module in the system — it should never need to import from M3, M4, or above).

**Future Extensibility:** This is the primary extension point of the whole Platform. Adding a new connector means: (1) implement the shared connector interface, (2) register it against the identifier type(s) it handles. Nothing else in the system changes. This is the module future connectors (breach-checking sources, additional social platforms, blockchain explorers for wallet addresses, etc., see Section 19) will plug into.

---

### 11.3 M3 — Data Normalization Engine

**Purpose:** Guarantee that every downstream module (correlation, graph, profile, timeline, report) only ever has to understand one data shape, regardless of which of the (currently six, eventually many more) connectors produced it.

**Responsibilities:**
- Define the shared internal schema for a normalized fact. Conceptually, every normalized fact has: a `fact_type` (e.g., `email`, `domain_registration`, `certificate`, `archive_snapshot`, `social_account`, `avatar_hash`), a `value` or small set of attributes, an optional `occurred_at` timestamp (for timeline-eligible facts), a `source_connector` reference, and a `raw_reference` pointing back to the original raw response (for evidence/audit).
- Provide one normalization function per connector type that maps that connector's raw payload into zero or more normalized facts.
- Attach provenance to every normalized fact (which connector, which identifier, which raw response, when it was fetched).
- Reject/flag malformed or unparseable connector output rather than silently dropping or guessing.

**Inputs:** Raw response envelopes from M2 (via M1).

**Outputs:** A list of normalized facts, persisted via M9, and handed to M4 (Correlation Engine).

**Dependencies:** M2 (defines the raw shape being normalized), M9 (persistence).

**Future Extensibility:** New connectors require a new normalization mapping function, but the shared schema itself is designed to be a stable contract — new `fact_type` values can be added without breaking existing consumers, because M4/M5/M6/M7 are written to handle "a list of typed facts" generically rather than hard-coding assumptions about exactly six fact types.

---

### 11.4 M4 — Entity Correlation Engine

**Purpose:** Turn a pile of normalized facts into a small number of unified, evidence-backed entities and relationships — the actual analytical value of the Platform.

**Responsibilities:**
- Compare normalized facts within an investigation to detect matches: exact matches (same email string, same domain), and shared-attribute matches (e.g., a domain's WHOIS registrant email matches a Gravatar email already seen elsewhere in the investigation).
- Merge matched facts into a "unified entity" (e.g., a person or organization) that aggregates all the attributes discovered about it.
- Create relationship edges between unified entities when facts link them (e.g., "domain X was registered using email Y," "username Z's GitHub profile lists email Y").
- Assign a confidence score to every unified entity and every relationship edge, using a fixed, documented set of deterministic rules (e.g., exact-string match on a verified field = high confidence; indirect/derived match = medium confidence; heuristic proximity match, if ever added = low confidence). No machine learning, no opaque scoring — v1 uses simple, explicit, inspectable rules only.
- Record, for every score, exactly which rule and which evidence produced it, so it can be displayed in the UI (FR4.4).
- Re-run correlation whenever new facts are added to an investigation (e.g., after adding a new identifier), producing an updated but still deterministic result.

**Inputs:** Normalized facts (all facts belonging to one investigation) from M3.

**Outputs:** Unified entities + relationship edges + confidence scores, persisted via M9 and mirrored into Neo4j for graph queries (Section 14).

**Dependencies:** M3 (source of normalized facts), M9 (persistence to PostgreSQL and Neo4j).

**Future Extensibility:** The rule set is intentionally isolated behind one clear function ("given two facts, do they match, and with what confidence") so it can be extended with new rules, or eventually replaced/augmented with a learned model, without changing how M5/M6/M7/M8 consume unified entities and relationships. This is the described but not-yet-designed evolution path toward the future "AI Investigation Copilot" (Section 19).

---

### 11.5 M5 — Interactive Relationship Graph

**Purpose:** Let the investigator see, not just read, how discovered entities relate to each other.

**Responsibilities:**
- Render unified entities as nodes and relationship edges as, well, edges, using Cytoscape.js.
- Support pan/zoom/drag and basic layout (force-directed or hierarchical, chosen for demo clarity).
- On node click: show the entity's attributes, confidence score, and full evidence list (which facts, which connectors, which raw responses contributed to it).
- On edge click: show the relationship type, its confidence score, and the evidence that produced it.
- Support visually distinguishing confidence levels (e.g., edge/node styling by confidence tier).

**Inputs:** Unified entities + relationships from M4 (queried via the backend API, Section 15), typically sourced from Neo4j for graph-shaped queries.

**Outputs:** Rendered interactive graph in the browser; also the source of the "graph snapshot image" embedded into the PDF report (M8), captured client-side or server-side as an image export.

**Dependencies:** M4 (data), backend API layer (Section 15).

**Future Extensibility:** Node/edge click handlers are built generically against "an entity with attributes and evidence" / "a relationship with a type and evidence," so future entity or relationship types (e.g., from new connectors) render without frontend changes.

---

### 11.6 M6 — Unified Identity Profile

**Purpose:** Give the investigator a single, readable "profile card" per unified entity — the human-readable counterpart to the graph's visual one.

**Responsibilities:**
- Display, per unified entity: associated emails, phones, usernames, domains, social accounts, an overall confidence indicator, and the full evidence/source list backing each attribute.
- Allow navigating from any attribute directly to its supporting evidence (raw connector response reference).
- Reflect updates when correlation is re-run after new identifiers are added.

**Inputs:** Unified entity data from M4 (via backend API).

**Outputs:** Rendered profile view in the browser; also a primary content block embedded into the PDF report (M8).

**Dependencies:** M4, backend API layer.

**Future Extensibility:** Designed as a generic renderer over "attribute categories with evidence," so new fact/attribute types introduced by future connectors appear automatically without new frontend code, as long as M3 tags them with a recognized category.

---

### 11.7 M7 — Investigation Timeline

**Purpose:** Reconstruct a chronological narrative from otherwise scattered dated facts.

**Responsibilities:**
- Collect all normalized facts that carry an `occurred_at` timestamp (e.g., domain registration date, certificate issuance date, Wayback snapshot date).
- Sort and render them chronologically.
- Allow filtering by unified entity or by event/fact type.
- Link each timeline entry back to its supporting evidence.

**Inputs:** Normalized facts (specifically the timestamped subset) from M3, and their entity associations from M4.

**Outputs:** Rendered timeline view in the browser; a content block embedded into the PDF report (M8).

**Dependencies:** M3, M4, backend API layer.

**Future Extensibility:** New connectors that introduce new kinds of dated events (e.g., a future breach-date connector) automatically populate the timeline as long as they set `occurred_at` during normalization — no timeline-specific code changes needed.

---

### 11.8 M8 — PDF Investigation Report

**Purpose:** Produce a professional, self-contained, shareable artifact that captures the full state of an investigation at export time.

**Responsibilities:**
- Assemble a report containing: executive summary, unified identity profile(s) (M6 data), a graph snapshot image (M5's rendered state, exported as an image), the investigation timeline (M7 data), a full evidence appendix, a list of sources/connectors used, and confidence scores throughout.
- Render this content into a PDF using ReportLab, following a consistent, professional layout (title page, table of contents, section per investigation aspect).
- Allow regenerating the report on demand so it always reflects the current state of the investigation.
- Store the generated report (or enough information to regenerate it) so it can be re-downloaded later without re-running the whole pipeline.

**Inputs:** Aggregated data from M4 (entities/relationships), M6 (profile view data), M7 (timeline data), and a graph snapshot image from M5.

**Outputs:** A downloadable PDF file, persisted via M9.

**Dependencies:** M4, M5 (for the snapshot image), M6, M7, M9.

**Future Extensibility:** The report is built as a sequence of independent "section builders" (summary section, profile section, graph section, timeline section, evidence section). A future report type (e.g., a shorter "risk dashboard" export, Section 19) can reuse the same section builders rather than rewriting rendering logic.

---

### 11.9 M9 — Investigation & Persistence Layer

**Purpose:** Own the concept of an "investigation" as the unit that ties every other module's data together, and provide one consistent persistence boundary for the whole system.

**Responsibilities:**
- Define and persist the `Investigation` entity (id, name, created_at, status) as the parent record for everything else.
- Persist identifiers submitted to an investigation.
- Persist raw connector responses (with provenance) — PostgreSQL.
- Persist normalized facts — PostgreSQL.
- Persist unified entities and relationships — PostgreSQL as source of truth, mirrored into Neo4j for graph queries (Section 14 explains the split in detail).
- Persist generated reports (or their regeneration inputs).
- Provide the query interfaces the other modules need (e.g., "all normalized facts for investigation X," "all unified entities for investigation X").

**Inputs:** Write/read calls from every other module.

**Outputs:** Persisted, queryable state.

**Dependencies:** PostgreSQL, Neo4j.

**Future Extensibility:** Because every other module talks to persistence only through this layer's interface (not directly to SQL/Cypher), the actual storage technology could be swapped later without touching M1–M8's logic — though no such swap is planned or needed for v1.

---

## 12. Data Flow

End-to-end flow for a single identifier being investigated, tying the modules together:

```
[Investigator submits identifier] 
        │
        ▼
   M9: create/append to Investigation record
        │
        ▼
   M1 (Search Orchestrator)
        │  looks up applicable connectors via M2 registry
        ▼
   M2 (Connector Framework)
        │  executes WHOIS / RDAP / crt.sh / Wayback / GitHub / Gravatar
        │  as applicable to this identifier's type
        ▼
   raw response envelopes  ───────► M9 (persist raw, with provenance)
        │
        ▼
   M3 (Normalization Engine)
        │  maps each raw envelope → normalized fact(s)
        ▼
   normalized facts  ─────────────► M9 (persist normalized facts)
        │
        ▼
   M4 (Entity Correlation Engine)
        │  compares facts across the whole investigation
        │  merges matches → unified entities + relationship edges
        │  assigns confidence scores with recorded rule/evidence
        ▼
   unified entities + relationships ─► M9 (persist to Postgres + mirror to Neo4j)
        │
        ├──► M5 (Graph view) ── reads from Neo4j for graph queries
        ├──► M6 (Profile view) ── reads consolidated entity data
        ├──► M7 (Timeline view) ── reads timestamped facts + entity links
        │
        ▼
   M8 (Report Generator)
        │  pulls current state from M4/M5/M6/M7
        ▼
   Downloadable PDF ─────────────► M9 (persist report)
```

Key property preserved throughout: **every arrow in this diagram carries data that still points back to its origin.** A unified entity always knows which normalized facts built it; a normalized fact always knows which raw response and connector produced it. This provenance chain is what makes FR4.4 (explainability) and NFR4/NFR9 (explainability/auditability) possible, and it is the single most important invariant in this system — no future change should break the ability to trace a displayed fact back to its raw evidence.

---

## 13. Folder Structure (High Level Only)

This is intentionally high-level. Exact file names within each folder are an implementation detail left to the coding phase, not fixed by this document.

```
osint-aggregator/
├── backend/
│   ├── app/
│   │   ├── orchestrator/        # M1 — Search Orchestrator
│   │   ├── connectors/          # M2 — Connector Framework
│   │   │   ├── base/            # shared interface + HTTP plumbing
│   │   │   ├── whois/
│   │   │   ├── rdap/
│   │   │   ├── crtsh/
│   │   │   ├── wayback/
│   │   │   ├── github/
│   │   │   └── gravatar/
│   │   ├── normalization/       # M3 — Data Normalization Engine
│   │   ├── correlation/         # M4 — Entity Correlation Engine
│   │   ├── reporting/           # M8 — PDF Investigation Report
│   │   ├── investigations/      # M9 — Investigation & Persistence Layer
│   │   ├── api/                 # FastAPI routers (Section 15)
│   │   └── main.py              # FastAPI app entry point
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── views/
│   │   │   ├── graph/           # M5 — Interactive Relationship Graph
│   │   │   ├── profile/         # M6 — Unified Identity Profile
│   │   │   └── timeline/        # M7 — Investigation Timeline
│   │   ├── components/
│   │   ├── api/                 # typed API client
│   │   └── App.tsx
│   ├── package.json
│   └── tsconfig.json
├── docs/
│   └── MASTER_DESIGN.md         # this document
└── docker-compose.yml           # Postgres + Neo4j + backend + frontend
```

This structure mirrors the module breakdown (Section 10) directly on purpose: a contributor (human or AI) reading Section 11 for a module should be able to find its code in exactly one obviously-named folder.

---

## 14. Database Overview (Not Full Schema)

No table-by-table or property-by-property schema is defined here — that is implementation detail for the coding phase. This section describes only the conceptual data groupings and why each lives where it does.

### 14.1 PostgreSQL — System of Record

PostgreSQL holds everything that is fundamentally record-shaped and needs transactional integrity:

- **Investigations** — the top-level case record.
- **Identifiers** — the inputs submitted for an investigation.
- **Connector executions** — status/timing/errors per connector run.
- **Raw responses** — the untouched connector output, with provenance links back to the connector execution that produced it.
- **Normalized facts** — the M3 output, with provenance links back to the raw response.
- **Unified entities & relationships** — the M4 output, stored here as the durable source of truth even though they are also mirrored into Neo4j.
- **Reports** — generated report metadata and either the stored PDF or the data needed to regenerate it.

PostgreSQL is chosen because it is simple, ubiquitous, transactional, and requires no special operational knowledge — appropriate for NFR1 and NFR8.

### 14.2 Neo4j — Graph Query & Visualization Layer

Neo4j holds a **mirror** of unified entities (as nodes) and relationships (as edges), kept in sync whenever M4 produces new or updated correlation results. It exists purely because the Interactive Relationship Graph (M5) needs queries like "show me everything connected to this entity within two hops" or "find the shortest evidentiary path between these two entities," which are natural, fast, single queries in a graph database and awkward, multi-join queries in a relational one.

**PostgreSQL remains authoritative.** If the Neo4j mirror were ever lost or needed rebuilding, it can be fully regenerated from PostgreSQL's unified entities and relationships table. This keeps the system's actual state in one place (avoiding split-brain data integrity problems) while still getting native graph-query ergonomics where they matter.

### 14.3 What Is Deliberately Not Designed Here

- Exact column/property names and types.
- Indexing strategy.
- Migration tooling choice.
- Full Cypher query patterns.

These are correctly left to the implementation phase and should be filled in by whichever AI model or developer picks up the corresponding module, guided by the conceptual groupings above.

---

## 15. API Overview (Major Endpoints Only)

This is a conceptual endpoint map, not a full API specification (no request/response bodies are defined here — that is implementation detail).

| Area | Endpoint (conceptual) | Purpose |
|---|---|---|
| Investigations | `POST /investigations` | Create a new investigation. |
| Investigations | `GET /investigations/{id}` | Retrieve an investigation's current state/summary. |
| Investigations | `GET /investigations` | List existing investigations. |
| Identifiers | `POST /investigations/{id}/identifiers` | Add one or more identifiers to an investigation, triggering M1. |
| Orchestration | `GET /investigations/{id}/status` | Get per-connector execution status for polling/progress display. |
| Facts | `GET /investigations/{id}/facts` | Retrieve normalized facts (mainly for debugging/evidence drill-down). |
| Entities | `GET /investigations/{id}/entities` | Retrieve unified entities and relationships (backs M5 graph and M6 profile views). |
| Entities | `GET /investigations/{id}/entities/{entityId}` | Retrieve one unified entity's full profile and evidence. |
| Timeline | `GET /investigations/{id}/timeline` | Retrieve chronologically ordered dated events. |
| Reports | `POST /investigations/{id}/report` | Generate (or regenerate) the PDF report. |
| Reports | `GET /investigations/{id}/report` | Download the most recently generated report. |
| Auth | `POST /auth/login` | Minimal authentication gate (see NFR10). |

All endpoints operate within the scope of a single investigation except investigation creation/listing and auth — this keeps the API surface small and directly aligned with the module boundaries in Section 11.

---

## 16. Frontend Overview

**Stack:** React + TypeScript + Tailwind CSS.

**Structure:** One single-page application with three primary views over a shared investigation context (an investigation ID held in route/app state):

- **Graph View (M5):** Cytoscape.js canvas as the default landing view for an open investigation. Node/edge click opens a side panel with evidence detail.
- **Profile View (M6):** List/detail layout — list of unified entities on the left (or top, responsive), full profile detail on selection.
- **Timeline View (M7):** Vertical chronological list with filter controls (by entity, by event type).

A persistent top bar shows the current investigation name, connector execution status (from M1's status endpoint, polled while running), and an "Export Report" action (triggers M8).

**Design principles:**
- Every piece of derived information shown to the user (a merged entity, a confidence score, a timeline entry) must be clickable through to its underlying evidence — this is a direct UI expression of NFR4 (explainability).
- Loading and partial-progress states are first-class, not an afterthought — connector execution is not instantaneous, and the UI should show progress rather than a single blocking spinner (supports FR2.3).
- No client-side state layer beyond what React itself provides is required for v1; there is no need for a heavy global state management library given the size of the app.

---

## 17. Backend Overview

**Stack:** FastAPI (Python).

**Structure:** One FastAPI application exposing the endpoints in Section 15, internally delegating to the module implementations described in Section 11 (M1–M4, M8, M9), which live in clearly separated packages (Section 13).

**Execution model:** Connector execution (M2, orchestrated by M1) runs asynchronously within the FastAPI process using Python's `async`/`await` and an async HTTP client, allowing multiple connectors to run concurrently for the same identifier without needing an external task queue or worker cluster. This is the simplest option that satisfies NFR5 (resilience to partial failure) and NFR6 (reasonable performance) without introducing the operational complexity explicitly ruled out in the project brief (no Kubernetes, no distributed systems).

**Configuration:** Connector API keys/tokens (where a source requires one, e.g., GitHub for higher rate limits) are read from environment variables at startup, never hard-coded (NFR10).

**Error handling:** Each connector call is wrapped so that a failure (timeout, rate limit, malformed response) is captured as a structured error result rather than raised as an unhandled exception, preserving FR2.4/NFR5.

---

## 18. Technology Decisions

| Layer | Choice | Why |
|---|---|---|
| Frontend | React + TypeScript | Widely known, strong typing reduces integration errors between modules built by different contributors/AI models. |
| Styling | Tailwind CSS | Fast to iterate within a hackathon timeframe; no separate design system needed for v1. |
| Backend | FastAPI (Python) | Async-native (fits the concurrent-connector execution model in Section 17), strong typing via Pydantic, fast to build REST APIs with. |
| Relational DB | PostgreSQL | Mature, transactional, simple to self-host; system of record (Section 14.1). |
| Graph DB | Neo4j | Native graph queries for the relationship graph feature; avoids painful multi-join relational queries for connected-entity lookups (Section 14.2). |
| Graph Visualization | Cytoscape.js | Purpose-built for interactive node/edge graphs in the browser; directly fits M5's requirements. |
| PDF Generation | ReportLab | Mature Python PDF library; integrates naturally with the FastAPI backend for M8 without a separate rendering service. |
| Deployment | docker-compose (Postgres + Neo4j + backend + frontend) | Satisfies NFR8 (local-first/self-hostable) without container orchestration. |

No other infrastructure (message queues, caching layers, container orchestration, service meshes) is included in v1. If a future need for any of these arises, it should be justified against a specific, demonstrated bottleneck — not added speculatively.

---

## 19. Future Expansion

The following features are explicitly deferred and **not designed** in this document. They are listed here only so that current architectural decisions (module boundaries, the shared normalized schema, the connector interface, the section-builder structure of the report) are made with awareness that these will eventually need to plug in.

- AI Investigation Copilot
- Risk Dashboard
- Investigation Replay
- Reverse Image Search
- Continuous Monitoring
- Local Language Matching
- Natural Language Queries
- Workspace
- Monitoring Alerts

No further detail on these is provided by design (per the project brief). Any future design work on these features should begin as its own addendum document that references, and does not contradict, this one.

---

## 20. Development Roadmap

A hackathon-appropriate, incremental roadmap. Each phase should produce something demoable.

**Phase 0 — Skeleton**
- Set up docker-compose (Postgres, Neo4j, backend, frontend).
- Stand up empty FastAPI app and empty React app that can talk to each other.
- Define the Investigation model end-to-end (create, retrieve) — proves M9's core shape.

**Phase 1 — One Connector, End to End**
- Implement the connector interface (M2) with a single connector (recommended: WHOIS, since domains are simple to test with).
- Implement M1 orchestration for exactly one connector.
- Implement M3 normalization for WHOIS output only.
- Store raw + normalized data. No correlation or graph yet.
- **Demo milestone:** submit a domain, see normalized WHOIS facts stored and retrievable.

**Phase 2 — Full Connector Set**
- Add RDAP, crt.sh, Wayback Machine, GitHub, Gravatar connectors and their normalization mappings.
- Confirm the orchestrator correctly fans out per identifier type and handles partial failures (FR2.4).
- **Demo milestone:** submit an email + a domain, see normalized facts from multiple sources.

**Phase 3 — Correlation**
- Implement the deterministic matching rules and confidence scoring (M4).
- Persist unified entities/relationships to PostgreSQL; mirror to Neo4j.
- **Demo milestone:** two connectors' facts about the same email merge into one unified entity with a visible confidence score.

**Phase 4 — Visualization**
- Build the Graph view (M5) against Neo4j-backed API endpoints.
- Build the Profile view (M6).
- Build the Timeline view (M7).
- **Demo milestone:** full click-through from graph node → evidence, and a working timeline.

**Phase 5 — Reporting**
- Implement the PDF report (M8): section builders for summary, profile, graph snapshot, timeline, evidence appendix.
- **Demo milestone:** one-click PDF export of a completed investigation.

**Phase 6 — Polish for Demo**
- Minimal auth gate (NFR10).
- Progress indicators, error states, empty states in the frontend.
- Sample/seed investigation for a smooth live demo.

This roadmap intentionally sequences work so that after Phase 1 there is already something end-to-end working, and every subsequent phase adds one clearly-scoped capability without requiring rework of earlier phases — a direct consequence of the module boundaries defined in Section 11.

---

*End of MASTER_DESIGN.md. Any AI model or developer beginning a coding task on this project should have read this entire document first. If a requested change would violate a module boundary or invariant described above (especially the provenance chain in Section 12), flag the conflict before proceeding rather than silently working around it.*
