/**
 * FastAPI DataProvider implementation.
 * 
 * This is the production data provider that connects to the FastAPI backend.
 * It implements the DataProvider interface and maps backend DTOs to frontend
 * domain types using the mappers module.
 * 
 * All components consume data through the DataProvider interface, so swapping
 * this provider in place of mockDataProvider requires no component changes.
 */

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

import type { DataProvider } from "./data-provider";
import { apiClient, extractFilename, isNotFoundError } from "./client";
import {
  deriveDashboardStats,
  mapConnectorResultList,
  mapExecutionResult,
  mapFrontendIdentifierType,
  mapGeneratedReport,
  mapIdentifierList,
  mapInvestigation,
  mapInvestigationList,
  mapTimelineResponse,
} from "./mappers";
import {
  graphFixture,
  identityProfileFixture,
} from "./mock-fixtures";

/**
 * FastAPI-backed implementation of the DataProvider interface.
 */
class FastAPIDataProvider implements DataProvider {
  // =========================================================================
  // Read Operations
  // =========================================================================

  async listInvestigations(): Promise<Investigation[]> {
    const response = await apiClient.get<{
      items: Array<{
        id: string;
        name: string;
        status: "created" | "running" | "completed" | "failed";
        created_at: string;
        updated_at: string;
      }>;
      count: number;
    }>("/api/v1/investigations/investigations", {
      params: { skip: 0, limit: 100 },
    });

    return mapInvestigationList(response.data);
  }

  async getInvestigation(id: string): Promise<Investigation | undefined> {
    try {
      const response = await apiClient.get<{
        id: string;
        name: string;
        status: "created" | "running" | "completed" | "failed";
        created_at: string;
        updated_at: string;
      }>(`/api/v1/investigations/investigations/${id}`);

      return mapInvestigation(response.data);
    } catch (error) {
      // Return undefined for 404s, rethrow other errors
      if (isNotFoundError(error)) {
        return undefined;
      }
      throw error;
    }
  }

  async listIdentifiers(investigationId?: string): Promise<Identifier[]> {
    if (!investigationId) return [];

    try {
      const response = await apiClient.get<{
        items: Array<{
          id: string;
          type: string;
          value: string;
          confidence: number;
          sources: number;
          first_seen: string;
        }>;
        count: number;
      }>(`/api/v1/investigations/investigations/${investigationId}/identifiers`);

      return mapIdentifierList(response.data);
    } catch (error) {
      if (isNotFoundError(error)) return [];
      throw error;
    }
  }

  async listConnectors(investigationId?: string): Promise<Connector[]> {
    if (!investigationId) return [];

    try {
      const response = await apiClient.get<{
        items: Array<{
          id: string;
          name: string;
          category: string;
          status: string;
          hits: number;
          runtime: string;
        }>;
        count: number;
      }>(`/api/v1/investigations/investigations/${investigationId}/connectors`);

      return mapConnectorResultList(response.data);
    } catch (error) {
      if (isNotFoundError(error)) return [];
      throw error;
    }
  }

  async listTimeline(investigationId?: string): Promise<TimelineEvent[]> {
    if (!investigationId) {
      // Global timeline not supported yet - return empty array
      return [];
    }

    try {
      const response = await apiClient.get<{
        events: Array<{
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
        }>;
        count: number;
      }>(`/api/v1/investigations/investigations/${investigationId}/timeline`);

      return mapTimelineResponse(response.data);
    } catch (error) {
      if (isNotFoundError(error)) {
        return [];
      }
      throw error;
    }
  }

  async listReports(_investigationId?: string): Promise<Report[]> {
    // TODO: Backend endpoint not yet implemented
    // GET /api/v1/investigations/{id}/reports (list of reports)
    // For now, return empty array
    return [];
  }

  async getDashboardStats(): Promise<DashboardStat[]> {
    // Derive stats from investigation list until backend provides dedicated endpoint
    const investigations = await this.listInvestigations();
    return deriveDashboardStats(investigations);
  }

  async getIdentityProfile(_subjectId?: string): Promise<IdentityProfile> {
    // TODO: Future feature - requires M4 (Entity Correlation Engine)
    // For now, return mock data so identity page doesn't break
    return identityProfileFixture;
  }

  async getGraph(investigationId?: string): Promise<GraphData> {
    if (!investigationId) return graphFixture;

    try {
      const identifiers = await this.listIdentifiers(investigationId);
      if (!identifiers || identifiers.length === 0) return graphFixture;

      // Map identifier types to graph node types
      const typeMap: Record<string, import("@/types/domain").GraphNodeType> = {
        email: "email",
        domain: "domain",
        username: "user",
        wallet: "wallet",
        ip: "ip",
        social: "user",
        phone: "user",
      };

      // ── Hierarchical ring layout ─────────────────────────────────────────
      // Primary node at center. Secondary nodes are grouped by type and
      // placed in up to two concentric rings so same-type nodes cluster
      // together visually instead of making a dense star.
      const [primaryId, ...secondaryIds] = identifiers;

      const primaryNode: import("@/types/domain").GraphNode = {
        id: primaryId.id,
        label: primaryId.value.length > 28 ? primaryId.value.slice(0, 26) + "…" : primaryId.value,
        type: typeMap[primaryId.type] ?? "domain",
        x: 50,
        y: 50,
        size: 36,
        primary: true,
      };

      // Group secondaries by type to keep same-type nodes adjacent on ring
      const byType = new Map<string, typeof secondaryIds>();
      for (const id of secondaryIds) {
        const t = typeMap[id.type] ?? "domain";
        const arr = byType.get(t) ?? [];
        arr.push(id);
        byType.set(t, arr);
      }

      // Flatten back out, grouped by type — ring 1 ≤ 8 nodes, rest go to ring 2
      const grouped = Array.from(byType.values()).flat();
      const ring1 = grouped.slice(0, 8);
      const ring2 = grouped.slice(8);

      const buildRingNodes = (
        items: typeof secondaryIds,
        radius: number,
        offsetAngle = 0,
      ): import("@/types/domain").GraphNode[] =>
        items.map((id, i) => {
          const angle = offsetAngle + (2 * Math.PI * i) / items.length;
          return {
            id: id.id,
            label: id.value.length > 28 ? id.value.slice(0, 26) + "…" : id.value,
            type: typeMap[id.type] ?? "domain",
            x: Math.round(50 + radius * Math.cos(angle - Math.PI / 2)),
            y: Math.round(50 + radius * Math.sin(angle - Math.PI / 2)),
            size: 24,
            primary: false,
          };
        });

      const ring1Nodes = buildRingNodes(ring1, identifiers.length === 1 ? 0 : 28);
      const ring2Nodes = buildRingNodes(ring2, 42, Math.PI / ring2.length || 0);
      const nodes: import("@/types/domain").GraphNode[] = [primaryNode, ...ring1Nodes, ...ring2Nodes];

      // ── Edges ─────────────────────────────────────────────────────────────
      const edges: import("@/types/domain").GraphEdge[] = [];

      // All ring-1 nodes connect to primary
      for (const n of ring1Nodes) {
        edges.push({ from: primaryNode.id, to: n.id, kind: "related-to" });
      }
      // Ring-2 nodes connect to the nearest ring-1 node of matching type, or primary
      for (const n of ring2Nodes) {
        const peer = ring1Nodes.find((r) => r.type === n.type) ?? primaryNode;
        edges.push({ from: peer.id, to: n.id, kind: "same-type" });
      }
      // Cross-link same-type ring-1 nodes (max 2 per type group)
      const r1ByType = new Map<string, string[]>();
      for (const n of ring1Nodes) {
        const arr = r1ByType.get(n.type) ?? [];
        arr.push(n.id);
        r1ByType.set(n.type, arr);
      }
      for (const ids of r1ByType.values()) {
        for (let i = 0; i < Math.min(ids.length - 1, 2); i++) {
          edges.push({ from: ids[i], to: ids[i + 1], kind: "same-type" });
        }
      }

      return { nodes, edges };
    } catch {
      return graphFixture;
    }
  }

  // =========================================================================
  // Mutation Operations
  // =========================================================================

  async createInvestigation(
    input: NewInvestigationInput
  ): Promise<Investigation> {
    const response = await apiClient.post<{
      id: string;
      name: string;
      status: "created" | "running" | "completed" | "failed";
      created_at: string;
      updated_at: string;
      seed_identifier?: {
        value: string;
        type: string;
      } | null;
    }>("/api/v1/investigations/investigations", {
      name: input.name,
      // Persist the seed identifier so it survives page reloads
      seed_identifier: input.target
        ? {
            value: input.target,
            type: mapFrontendIdentifierType(input.seedType),
          }
        : undefined,
    });

    return mapInvestigation(response.data);
  }

  async executeInvestigation(
    investigationId: string,
    identifier: { value: string; type: IdentifierType }
  ): Promise<ExecutionResult> {
    const response = await apiClient.post<{
      investigation_id: string;
      status: "created" | "running" | "completed" | "failed";
      started_at: string;
      finished_at: string;
      statistics: {
        executed_connectors: number;
        successful_connectors: number;
        failed_connectors: number;
        connector_results_count: number;
        normalized_facts_count: number;
        execution_duration_seconds: number;
      };
      connector_results: Array<{
        connector_name: string;
        status: string;
        started_at: string | null;
        finished_at: string | null;
        error_message: string | null;
      }>;
    }>(`/api/v1/investigations/investigations/${investigationId}/execute`, {
      identifier: identifier.value,
      type: mapFrontendIdentifierType(identifier.type),
    });

    return mapExecutionResult(response.data);
  }

  async generateReport(investigationId: string): Promise<GeneratedReport> {
    const response = await apiClient.post<{
      id: string;
      investigation_id: string;
      status: "pending" | "generating" | "completed" | "failed";
      file_size: number;
      generated_at: string;
    }>(`/api/v1/investigations/investigations/${investigationId}/report`);

    return mapGeneratedReport(response.data);
  }

  async downloadReport(
    investigationId: string,
    _reportId?: string
  ): Promise<ReportDownload> {
    // Backend endpoint: GET /api/v1/investigations/{id}/report
    // Returns binary PDF with Content-Disposition header
    const response = await apiClient.get(
      `/api/v1/investigations/investigations/${investigationId}/report`,
      {
        responseType: "blob",
      }
    );

    // Extract filename from Content-Disposition header
    const contentDisposition = response.headers["content-disposition"];
    const filename = extractFilename(contentDisposition);

    // Create object URL for the blob
    const blob = new Blob([response.data], { type: "application/pdf" });
    const url = URL.createObjectURL(blob);

    return {
      reportId: _reportId || `RPT-${investigationId}`,
      filename,
      contentType: "application/pdf",
      url,
    };
  }
}

/**
 * Singleton instance of the FastAPI provider.
 */
export const fastAPIProvider = new FastAPIDataProvider();
