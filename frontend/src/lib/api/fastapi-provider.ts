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
  mapExecutionResult,
  mapGeneratedReport,
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

  async listIdentifiers(_investigationId?: string): Promise<Identifier[]> {
    // TODO: Backend endpoint not yet implemented
    // GET /api/v1/investigations/{id}/identifiers
    // For now, return empty array - investigation detail page will handle gracefully
    return [];
  }

  async listConnectors(_investigationId?: string): Promise<Connector[]> {
    // TODO: Backend endpoint not yet implemented
    // GET /api/v1/investigations/{id}/connectors
    // For now, return empty array - investigation detail page will handle gracefully
    return [];
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

  async getGraph(_investigationId?: string): Promise<GraphData> {
    // TODO: Future feature - requires M4 + Neo4j integration
    // For now, return mock data so graph page doesn't break
    return graphFixture;
  }

  // =========================================================================
  // Mutation Operations
  // =========================================================================

  async createInvestigation(
    input: NewInvestigationInput
  ): Promise<Investigation> {
    // Backend currently only accepts name
    // Store other fields (target, severity, etc.) for future use
    const response = await apiClient.post<{
      id: string;
      name: string;
      status: "created" | "running" | "completed" | "failed";
      created_at: string;
      updated_at: string;
    }>("/api/v1/investigations/investigations", {
      name: input.name,
    });

    const investigation = mapInvestigation(response.data);
    
    // Enhance with frontend-provided fields
    // These aren't persisted yet but improve UX
    investigation.target = input.target;
    investigation.severity = input.severity;
    investigation.identifiers = input.seedIdentifiers.length;

    return investigation;
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
      type: identifier.type,
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
