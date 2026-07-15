// Data-provider abstraction.
//
// Pages and components consume data via this contract; they never import the
// mock fixtures directly. To wire the frontend to the real FastAPI backend
// (endpoints listed in `src/types/domain.ts`), implement `DataProvider` with
// `fetch`-based calls and register it via `setDataProvider(...)` from a
// bootstrap file — pages and hooks will not need to change.

import type {
  Connector,
  DashboardStat,
  ExecutionResult,
  GeneratedReport,
  GraphData,
  Identifier,
  IdentifierType,
  IdentityProfile,
  Investigation,
  NewInvestigationInput,
  Report,
  ReportDownload,
  TimelineEvent,
} from "@/types/domain";
import {
  connectorsFixture,
  graphFixture,
  identifiersFixture,
  identityProfileFixture,
  investigationsFixture,
  reportsFixture,
  timelineFixture,
} from "./mock-fixtures";

export interface DataProvider {
  // Reads
  listInvestigations(): Promise<Investigation[]>;
  getInvestigation(id: string): Promise<Investigation | undefined>;
  listIdentifiers(investigationId?: string): Promise<Identifier[]>;
  listConnectors(investigationId?: string): Promise<Connector[]>;
  listTimeline(investigationId?: string): Promise<TimelineEvent[]>;
  listReports(investigationId?: string): Promise<Report[]>;
  getDashboardStats(): Promise<DashboardStat[]>;
  // The following two endpoints do not exist in the current FastAPI backend
  // yet — pages consume them exclusively through this provider so a future
  // backend module can supply them without page changes.
  getIdentityProfile(subjectId?: string): Promise<IdentityProfile>;
  getGraph(investigationId?: string): Promise<GraphData>;

  // Mutations (aligned with existing backend endpoints)
  createInvestigation(input: NewInvestigationInput): Promise<Investigation>;
  executeInvestigation(
    investigationId: string,
    identifier: { value: string; type: IdentifierType },
  ): Promise<ExecutionResult>;
  generateReport(investigationId: string): Promise<GeneratedReport>;
  downloadReport(investigationId: string, reportId?: string): Promise<ReportDownload>;
}

// ---- Mock implementation ---------------------------------------------------
// Async signature keeps the contract identical when a real HTTP-backed
// provider replaces it. Dashboard stats are derived from the investigation
// collection so that once the FastAPI provider is wired in, the same
// aggregation shape lights up automatically.

function deriveDashboardStats(list: Investigation[]): DashboardStat[] {
  const total = list.length;
  const running = list.filter((i) => i.status === "active" || i.status === "pending").length;
  const completed = list.filter((i) => i.status === "completed").length;
  const failed = list.filter((i) => i.status === "failed").length;

  return [
    { label: "Total Investigations", value: total, delta: `${total} tracked`, trend: "up", tone: "cyan" },
    { label: "Running", value: running, delta: `${running} in progress`, trend: "up", tone: "violet" },
    { label: "Completed", value: completed, delta: `${completed} closed`, trend: "up", tone: "warning" },
    { label: "Failed", value: failed, delta: failed === 0 ? "no failures" : `${failed} to review`, trend: failed === 0 ? "down" : "warn", tone: "danger" },
  ];
}

export const mockDataProvider: DataProvider = {
  async listInvestigations() {
    return investigationsFixture;
  },
  async getInvestigation(id) {
    return investigationsFixture.find((i) => i.id === id);
  },
  async listIdentifiers() {
    return identifiersFixture;
  },
  async listConnectors() {
    return connectorsFixture;
  },
  async listTimeline(investigationId) {
    if (!investigationId) return timelineFixture;
    // Placeholder scope: current fixtures are not per-case, but keep the arg
    // wired so pages already pass it once the backend segments per case.
    return timelineFixture;
  },
  async listReports(investigationId) {
    if (!investigationId) return reportsFixture;
    return reportsFixture.filter((r) => r.investigation === investigationId);
  },
  async getDashboardStats() {
    return deriveDashboardStats(investigationsFixture);
  },
  async getIdentityProfile() {
    return identityProfileFixture;
  },
  async getGraph() {
    return graphFixture;
  },

  // Mutations — mock, no HTTP. Shape mirrors the backend response.
  async createInvestigation(input) {
    const now = new Date().toISOString();
    const nextNumber = investigationsFixture.reduce((max, inv) => {
      const n = Number(inv.id.split("-")[1]);
      return Number.isFinite(n) && n > max ? n : max;
    }, 1000) + 1;
    const created: Investigation = {
      id: `INV-${nextNumber}`,
      name: input.name || "Untitled Investigation",
      target: input.seedIdentifiers[0] ?? input.target,
      status: "pending",
      severity: input.severity,
      progress: 0,
      identifiers: input.seedIdentifiers.length,
      connectors: 0,
      createdAt: now,
      updatedAt: now,
      owner: "You",
      tags: [],
    };
    // Optimistic local append so the list reflects the new case in-session.
    investigationsFixture.unshift(created);
    return created;
  },
  async executeInvestigation(investigationId: string, identifier: { value: string; type: IdentifierType }) {
    return {
      investigationId,
      status: "queued" as const,
      startedAt: new Date().toISOString(),
    };
  },
  async generateReport(investigationId) {
    return {
      reportId: `RPT-${Date.now()}`,
      investigationId,
      status: "queued",
      createdAt: new Date().toISOString(),
    };
  },
  async downloadReport(investigationId, reportId) {
    return {
      reportId: reportId ?? `RPT-${investigationId}`,
      filename: `${investigationId}-report.pdf`,
      contentType: "application/pdf",
    };
  },
};

// Active provider - using mock data provider for now
let activeProvider: DataProvider = mockDataProvider;

export function setDataProvider(provider: DataProvider): void {
  activeProvider = provider;
}

export function getDataProvider(): DataProvider {
  return activeProvider;
}
