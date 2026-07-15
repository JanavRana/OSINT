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
  TimelineEvent,
  TimelineChannel,
  Severity,
  GeneratedReport,
  DashboardStat,
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
 * Map backend investigation to frontend Investigation.
 * 
 * Adds default values for fields that don't exist in backend yet.
 */
export function mapInvestigation(
  backend: BackendInvestigationRead
): Investigation {
  return {
    id: backend.id,
    name: backend.name,
    target: "", // Backend doesn't store target yet
    status: mapInvestigationStatus(backend.status),
    severity: "medium", // Default until backend supports it
    progress: backend.status === "completed" ? 100 : backend.status === "running" ? 50 : 0,
    identifiers: 0, // Will be populated when endpoint exists
    connectors: 0, // Will be populated when endpoint exists
    createdAt: backend.created_at,
    updatedAt: backend.updated_at,
    owner: "You", // Default until backend supports users
    tags: [], // Default until backend supports tags
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
