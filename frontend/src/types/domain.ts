// Domain types shared across the OSINT platform UI.
// These interfaces are the contract the backend (FastAPI) will populate.

export type InvestigationStatus = "active" | "completed" | "pending" | "failed";
export type Severity = "critical" | "high" | "medium" | "low";
export type ConnectorRunStatus = "success" | "running" | "queued" | "failed";
export type IdentifierType =
  | "email"
  | "domain"
  | "username"
  | "wallet"
  | "social"
  | "phone"
  | "ip";
export type TimelineChannel =
  | "email"
  | "wallet"
  | "domain"
  | "social"
  | "network"
  | "system";
export type ReportFormat = "PDF" | "HTML" | "JSON";

export interface Investigation {
  id: string;
  name: string;
  target: string;
  /** The persisted type of the seed identifier, if available. */
  seedType?: IdentifierType;
  status: InvestigationStatus;
  severity: Severity;
  progress: number;
  identifiers: number;
  connectors: number;
  createdAt: string;
  updatedAt: string;
  owner: string;
  tags: string[];
}

export interface Identifier {
  id: string;
  type: IdentifierType;
  value: string;
  confidence: number;
  sources: number;
  firstSeen: string;
}

export interface Connector {
  id: string;
  name: string;
  category: string;
  status: ConnectorRunStatus;
  hits: number;
  runtime: string;
}

export interface TimelineEvent {
  id: string;
  time: string;
  actor: string;
  action: string;
  target: string;
  channel: TimelineChannel;
  severity: Severity;
  details: string;
}

export interface Report {
  id: string;
  name: string;
  investigation: string;
  createdAt: string;
  pages: number;
  format: ReportFormat;
  size: string;
}

export type StatTone = "cyan" | "violet" | "warning" | "danger";
export type StatTrend = "up" | "down" | "warn";

export interface DashboardStat {
  label: string;
  value: string | number;
  delta: string;
  trend: StatTrend;
  tone: StatTone;
}

// Unified identity profile ---------------------------------------------------

export type IdentitySectionKey =
  | "emails"
  | "domains"
  | "usernames"
  | "wallets"
  | "social"
  | "phones"
  | "network";

export interface IdentityItem {
  value: string;
  confidence: number;
  sources: number;
  note: string;
}

export interface IdentitySection {
  key: IdentitySectionKey;
  title: string;
  items: IdentityItem[];
}

export interface EvidenceEntry {
  src: string;
  finding: string;
  conf: number;
}

export interface IdentityProfile {
  subjectId: string;
  displayName: string;
  initials: string;
  linkedInvestigation: string;
  totalIdentifiers: number;
  totalSources: number;
  overallConfidence: number;
  sections: IdentitySection[];
  evidence: EvidenceEntry[];
}

// Graph ----------------------------------------------------------------------

export type GraphNodeType = "email" | "domain" | "user" | "wallet" | "ip";

export interface GraphNode {
  id: string;
  label: string;
  type: GraphNodeType;
  x: number;
  y: number;
  size?: number;
  primary?: boolean;
}

export interface GraphEdge {
  from: string;
  to: string;
  kind: string;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

// Generic API envelope -------------------------------------------------------

export interface ApiListResponse<T> {
  items: T[];
  total: number;
}

export interface ApiError {
  message: string;
  code?: string;
  status?: number;
}

export interface AsyncResource<T> {
  data: T | undefined;
  isLoading: boolean;
  error: ApiError | null;
  refetch?: () => void;
}

// Mutations / write-side contracts -------------------------------------------
// These shapes align with the FastAPI backend's existing endpoints:
//   POST /api/v1/investigations                → createInvestigation
//   POST /api/v1/investigations/{id}/execute   → executeInvestigation
//   POST /api/v1/investigations/{id}/report    → generateReport
//   GET  /api/v1/investigations/{id}/report    → downloadReport
// A future FastAPIDataProvider fulfils this contract; pages call mutation
// hooks and never construct these payloads inline.

export interface NewInvestigationInput {
  name: string;
  target: string;
  severity: Severity;
  seedType: IdentifierType;
  seedIdentifiers: string[];
  notes?: string;
}

export type ExecutionStatus = "queued" | "running" | "completed" | "failed";

export interface ExecutionConnectorResult {
  connectorName: string;
  status: string;
  startedAt: string | null;
  finishedAt: string | null;
  errorMessage: string | null;
}

export interface ExecutionStatistics {
  executedConnectors: number;
  successfulConnectors: number;
  failedConnectors: number;
  connectorResultsCount: number;
  normalizedFactsCount: number;
  executionDurationSeconds: number;
}

export interface ExecutionResult {
  investigationId: string;
  status: ExecutionStatus;
  startedAt: string;
  finishedAt?: string;
  statistics?: ExecutionStatistics;
  connectorResults?: ExecutionConnectorResult[];
}

export interface GeneratedReport {
  reportId: string;
  investigationId: string;
  status: "queued" | "generating" | "ready" | "failed";
  createdAt: string;
}

export interface ReportDownload {
  reportId: string;
  filename: string;
  contentType: string;
  // Placeholder — a real provider will return a Blob / signed URL.
  url?: string;
}

export interface MutationResource<TInput, TOutput> {
  data: TOutput | undefined;
  isPending: boolean;
  error: ApiError | null;
  mutate: (input: TInput) => Promise<TOutput>;
  reset: () => void;
}
