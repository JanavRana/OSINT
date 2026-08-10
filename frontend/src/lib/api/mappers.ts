/**
 * DTO mappers for transforming backend DTOs to frontend domain types.
 * 
 * These adapters ensure that components only work with the frontend's
 * domain types and remain decoupled from backend response shapes.
 */

import type {
  Investigation,
  InvestigationStatus,
  ExecutionResult,
  ExecutionStatus,
  ExecutionConnectorResult,
  ExecutionStatistics,
  TimelineEvent,
  TimelineChannel,
  Severity,
  GeneratedReport,
  DashboardStat,
  Identifier,
  IdentifierType,
  Connector,
  ConnectorRunStatus,
} from "@/types/domain";

// ============================================================================
// Backend DTO Types
// ============================================================================

interface BackendInvestigationRead {
  id: string;
  name: string;
  status: "created" | "running" | "completed" | "failed";
  created_at: string;
  updated_at: string;
  seed_identifier?: {
    value: string;
    type: string;
  } | null;
}

interface BackendInvestigationList {
  items: BackendInvestigationRead[];
  count: number;
}

interface BackendExecutionStatistics {
  executed_connectors: number;
  successful_connectors: number;
  failed_connectors: number;
  connector_results_count: number;
  normalized_facts_count: number;
  execution_duration_seconds: number;
}

interface BackendConnectorExecutionResult {
  connector_name: string;
  status: string;
  started_at: string | null;
  finished_at: string | null;
  error_message: string | null;
}

interface BackendInvestigationExecuteResponse {
  investigation_id: string;
  status: "created" | "running" | "completed" | "failed";
  started_at: string;
  finished_at: string;
  statistics: BackendExecutionStatistics;
  connector_results: BackendConnectorExecutionResult[];
}

interface BackendTimelineEventResponse {
  id: string;
  investigation_id: string;
  entity_id: string | null;
  occurred_at: string;
  event_type: string;
  title: string;
  description: string;
  connector: string;
  source_fact_id: string;
  confidence: number;
}

interface BackendTimelineResponse {
  events: BackendTimelineEventResponse[];
  count: number;
}

interface BackendReportResponse {
  id: string;
  investigation_id: string;
  status: "pending" | "generating" | "completed" | "failed";
  file_size: number;
  generated_at: string;
}

// ============================================================================
// Mapper Functions
// ============================================================================

/**
 * Map backend InvestigationStatus to frontend InvestigationStatus.
 */
function mapInvestigationStatus(
  backendStatus: "created" | "running" | "completed" | "failed"
): InvestigationStatus {
  switch (backendStatus) {
    case "created":
      return "pending";
    case "running":
      return "active";
    case "completed":
      return "completed";
    case "failed":
      return "failed";
    default:
      return "pending";
  }
}

/**
 * Map backend investigation status to frontend ExecutionStatus.
 */
function mapExecutionStatus(
  backendStatus: "created" | "running" | "completed" | "failed"
): ExecutionStatus {
  switch (backendStatus) {
    case "created":
      return "queued";
    case "running":
      return "running";
    case "completed":
      return "completed";
    case "failed":
      return "failed";
    default:
      return "queued";
  }
}

/**
 * Derive severity from confidence score.
 */
function deriveSeverityFromConfidence(confidence: number): Severity {
  if (confidence >= 0.9) return "critical";
  if (confidence >= 0.7) return "high";
  if (confidence >= 0.5) return "medium";
  return "low";
}

/**
 * Derive channel from connector name and event type.
 */
function deriveChannel(
  connectorName: string,
  eventType: string
): TimelineChannel {
  const lowerConnector = connectorName.toLowerCase();
  const lowerEventType = eventType.toLowerCase();

  if (lowerConnector.includes("whois") || lowerConnector.includes("rdap") || lowerEventType.includes("domain")) {
    return "domain";
  }
  if (lowerConnector.includes("github") || lowerConnector.includes("twitter") || lowerEventType.includes("social")) {
    return "social";
  }
  if (lowerEventType.includes("email") || lowerConnector.includes("email")) {
    return "email";
  }
  if (lowerEventType.includes("wallet") || lowerConnector.includes("chain")) {
    return "wallet";
  }
  if (lowerEventType.includes("network") || lowerEventType.includes("ip")) {
    return "network";
  }
  
  return "system";
}

/**
 * Map backend IdentifierType string to frontend IdentifierType.
 * Backend uses "wallet_address"; frontend uses "wallet". Etc.
 */
export function mapBackendIdentifierType(
  backendType: string | undefined | null
): IdentifierType {
  switch (backendType) {
    case "email":         return "email";
    case "domain":        return "domain";
    case "username":      return "username";
    case "wallet_address": return "wallet";
    case "phone":         return "phone";
    case "image":         return "domain"; // no frontend image type
    default:              return "domain";
  }
}

/**
 * Map frontend IdentifierType to backend IdentifierType string.
 * Used when sending seed identifier in createInvestigation.
 */
export function mapFrontendIdentifierType(frontendType: IdentifierType): string {
  switch (frontendType) {
    case "email":    return "email";
    case "domain":   return "domain";
    case "username": return "username";
    case "wallet":   return "wallet_address";
    case "phone":    return "phone";
    case "social":   return "username"; // closest backend equivalent
    case "ip":       return "domain";   // no ip type in backend yet
    default:         return "domain";
  }
}

/**
 * Map backend investigation to frontend Investigation.
 *
 * Populates target and seedType from the persisted seed_identifier when
 * available (the fix for the "Run all connectors" disabled bug).
 */
export function mapInvestigation(
  backend: BackendInvestigationRead
): Investigation {
  const seed = backend.seed_identifier;
  return {
    id: backend.id,
    name: backend.name,
    target: seed?.value ?? "",
    seedType: seed ? mapBackendIdentifierType(seed.type) : undefined,
    status: mapInvestigationStatus(backend.status),
    severity: "medium", // Default until backend supports it
    progress: backend.status === "completed" ? 100 : backend.status === "running" ? 50 : 0,
    identifiers: 0, // Will be populated from the identifiers endpoint
    connectors: 0,  // Will be populated from the connectors endpoint
    createdAt: backend.created_at,
    updatedAt: backend.updated_at,
    owner: "You",  // Default until backend supports users
    tags: [],       // Default until backend supports tags
  };
}

/**
 * Map backend investigation list to frontend array.
 */
export function mapInvestigationList(
  backend: BackendInvestigationList
): Investigation[] {
  return backend.items.map(mapInvestigation);
}

/**
 * Map backend execution response to frontend ExecutionResult.
 */
export function mapExecutionResult(
  backend: BackendInvestigationExecuteResponse
): ExecutionResult {
  return {
    investigationId: backend.investigation_id,
    status: mapExecutionStatus(backend.status),
    startedAt: backend.started_at,
    finishedAt: backend.finished_at,
    statistics: backend.statistics
      ? {
          executedConnectors: backend.statistics.executed_connectors,
          successfulConnectors: backend.statistics.successful_connectors,
          failedConnectors: backend.statistics.failed_connectors,
          connectorResultsCount: backend.statistics.connector_results_count,
          normalizedFactsCount: backend.statistics.normalized_facts_count,
          executionDurationSeconds: backend.statistics.execution_duration_seconds,
        }
      : undefined,
    connectorResults: backend.connector_results?.map((cr) => ({
      connectorName: cr.connector_name,
      status: cr.status,
      startedAt: cr.started_at,
      finishedAt: cr.finished_at,
      errorMessage: cr.error_message,
    })),
  };
}

/**
 * Map backend timeline event to frontend TimelineEvent.
 */
export function mapTimelineEvent(
  backend: BackendTimelineEventResponse
): TimelineEvent {
  return {
    id: backend.id,
    time: backend.occurred_at,
    actor: backend.connector,
    action: backend.event_type,
    target: backend.entity_id || backend.title,
    channel: deriveChannel(backend.connector, backend.event_type),
    severity: deriveSeverityFromConfidence(backend.confidence),
    details: backend.description,
  };
}

/**
 * Map backend timeline response to frontend array.
 */
export function mapTimelineResponse(
  backend: BackendTimelineResponse
): TimelineEvent[] {
  return backend.events.map(mapTimelineEvent);
}

/**
 * Map backend report response to frontend GeneratedReport.
 */
export function mapGeneratedReport(
  backend: BackendReportResponse
): GeneratedReport {
  // Map status: "completed" -> "ready", "pending" -> "queued"
  let status: GeneratedReport["status"];
  switch (backend.status) {
    case "completed":
      status = "ready";
      break;
    case "pending":
      status = "queued";
      break;
    case "generating":
      status = "generating";
      break;
    case "failed":
      status = "failed";
      break;
    default:
      status = "queued";
  }

  return {
    reportId: backend.id,
    investigationId: backend.investigation_id,
    status,
    createdAt: backend.generated_at,
  };
}

/**
 * Derive dashboard stats from investigation list.
 * 
 * This is a client-side computation until the backend provides a stats endpoint.
 */
export function deriveDashboardStats(
  investigations: Investigation[]
): DashboardStat[] {
  const total = investigations.length;
  const running = investigations.filter(
    (i) => i.status === "active" || i.status === "pending"
  ).length;
  const completed = investigations.filter((i) => i.status === "completed").length;
  const failed = investigations.filter((i) => i.status === "failed").length;

  return [
    {
      label: "Total Investigations",
      value: total,
      delta: `${total} tracked`,
      trend: "up",
      tone: "cyan",
    },
    {
      label: "Running",
      value: running,
      delta: `${running} in progress`,
      trend: "up",
      tone: "violet",
    },
    {
      label: "Completed",
      value: completed,
      delta: `${completed} closed`,
      trend: "up",
      tone: "warning",
    },
    {
      label: "Failed",
      value: failed,
      delta: failed === 0 ? "no failures" : `${failed} to review`,
      trend: failed === 0 ? "down" : "warn",
      tone: "danger",
    },
  ];
}

// ============================================================================
// Identifier & Connector Mappers
// ============================================================================

interface BackendIdentifierRead {
  id: string;
  type: string;
  value: string;
  confidence: number;
  sources: number;
  first_seen: string;
  profile_url?: string | null;
  platform?: string | null;
  platform_display_name?: string | null;
}

interface BackendIdentifierListResponse {
  items: BackendIdentifierRead[];
  count: number;
}

interface BackendConnectorResultRead {
  id: string;
  name: string;
  category: string;
  status: string;
  hits: number;
  runtime: string;
}

interface BackendConnectorResultListResponse {
  items: BackendConnectorResultRead[];
  count: number;
}

function mapConnectorRunStatus(status: string): ConnectorRunStatus {
  switch (status) {
    case "success":
    case "succeeded":
      return "success";
    case "running":
      return "running";
    case "queued":
      return "queued";
    case "failed":
    case "timed_out":
      return "failed";
    default:
      return "queued";
  }
}

export function mapIdentifierList(
  backend: BackendIdentifierListResponse
): Identifier[] {
  return backend.items.map((item) => ({
    id: item.id,
    type: (item.type || "domain") as Identifier["type"],
    value: item.value,
    confidence: item.confidence,
    sources: item.sources,
    firstSeen: item.first_seen,
    profileUrl: item.profile_url ?? undefined,
    platform: item.platform ?? undefined,
    platformDisplayName: item.platform_display_name ?? undefined,
  }));
}

export function mapConnectorResultList(
  backend: BackendConnectorResultListResponse
): Connector[] {
  return backend.items.map((item) => ({
    id: item.id,
    name: item.name,
    category: item.category,
    status: mapConnectorRunStatus(item.status),
    hits: item.hits,
    runtime: item.runtime,
  }));
}
