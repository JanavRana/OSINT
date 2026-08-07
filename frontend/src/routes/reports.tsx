import { createFileRoute } from "@tanstack/react-router";
import { useCallback, useEffect, useRef, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  FileText, Download, Plus, Sparkles, ChevronRight, Clock, CheckCircle2,
  XCircle, Loader2, AlertTriangle,
} from "lucide-react";
import { AsyncBoundary, EmptyState } from "@/components/states";
import {
  useDownloadReport,
  useGenerateReport,
  useInvestigations,
} from "@/hooks/use-osint-data";
import { useSessionReports, type SessionReport } from "@/hooks/use-settings";
import { cn } from "@/lib/utils";
import { fmtDate } from "@/lib/format";
import type { Investigation } from "@/types/domain";

export const Route = createFileRoute("/reports")({
  head: () => ({ meta: [{ title: "Reports — AXIOM OSINT" }] }),
  component: ReportsPage,
});

// ─── Status icon ──────────────────────────────────────────────────────────────

function ReportStatusIcon({ status }: { status: SessionReport["status"] }) {
  switch (status) {
    case "ready":
      return <CheckCircle2 className="h-4 w-4 text-success" />;
    case "failed":
      return <XCircle className="h-4 w-4 text-destructive" />;
    case "generating":
      return <Loader2 className="h-4 w-4 text-primary animate-spin" />;
    default:
      return <Clock className="h-4 w-4 text-muted-foreground" />;
  }
}

const statusLabel: Record<SessionReport["status"], string> = {
  ready: "Ready",
  failed: "Failed",
  generating: "Generating",
  queued: "Queued",
};

const statusColor: Record<SessionReport["status"], string> = {
  ready: "text-success bg-success/15",
  failed: "text-destructive bg-destructive/15",
  generating: "text-primary bg-primary/15",
  queued: "text-muted-foreground bg-white/5",
};

// ─── Report list item ─────────────────────────────────────────────────────────

function ReportListItem({
  report,
  active,
  onSelect,
}: {
  report: SessionReport;
  active: boolean;
  onSelect: (r: SessionReport) => void;
}) {
  return (
    <button
      onClick={() => onSelect(report)}
      aria-pressed={active}
      className={cn(
        "w-full text-left rounded-xl p-4 border transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40",
        active
          ? "border-primary/50 bg-primary/[0.06] shadow-[0_0_20px_-6px_var(--primary)]"
          : "border-border/60 hover:border-border bg-card/60 glass"
      )}
    >
      <div className="flex items-start gap-3">
        <div className="h-10 w-10 rounded-lg bg-destructive/15 text-destructive grid place-items-center shrink-0" aria-hidden="true">
          <FileText className="h-4 w-4" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="font-medium text-sm truncate">
            Report — {report.investigationName}
          </div>
          <div className="text-[11px] text-muted-foreground font-mono mt-0.5">
            {report.investigationId} · {fmtDate(report.createdAt)}
          </div>
          <div className="mt-2 flex items-center gap-2 text-[10px]">
            <ReportStatusIcon status={report.status} />
            <span className={cn("px-1.5 py-0.5 rounded-full font-medium", statusColor[report.status])}>
              {statusLabel[report.status]}
            </span>
            <span className="text-muted-foreground">PDF</span>
          </div>
        </div>
        <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0" aria-hidden="true" />
      </div>
    </button>
  );
}

// ─── Report preview / details ─────────────────────────────────────────────────

function ReportPreview({
  report,
  investigation,
  onStatusUpdate,
}: {
  report: SessionReport;
  investigation?: Investigation;
  onStatusUpdate: (reportId: string, status: SessionReport["status"]) => void;
}) {
  const download = useDownloadReport();
  const generate = useGenerateReport();
  const isReady = report.status === "ready";
  const isFailed = report.status === "failed";
  const isPending = report.status === "queued" || report.status === "generating";

  // ── Polling: check status every 3s while queued/generating ─────────────────
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  }, []);

  const pollStatus = useCallback(async () => {
    if (!report.investigationId) return;
    try {
      // Re-generate (idempotent on backend) or call a status endpoint.
      // Since our backend endpoint is POST-to-generate, we re-issue the
      // generate call — if the PDF already exists the backend returns its
      // current status. This is the safest path without a dedicated GET status.
      const result = await generate.mutate(report.investigationId);
      const newStatus: SessionReport["status"] =
        result.status === "ready"
          ? "ready"
          : result.status === "failed"
          ? "failed"
          : result.status === "generating"
          ? "generating"
          : "queued";

      onStatusUpdate(report.reportId, newStatus);

      if (newStatus === "ready" || newStatus === "failed") {
        stopPolling();
      }
    } catch {
      // Don't stop polling on network errors — try again next interval
    }
  }, [report.investigationId, report.reportId, generate, onStatusUpdate, stopPolling]);

  useEffect(() => {
    if (isPending) {
      // Start polling
      pollingRef.current = setInterval(pollStatus, 3000);
    } else {
      stopPolling();
    }
    return stopPolling;
  }, [isPending, pollStatus, stopPolling]);

  // ── Download ────────────────────────────────────────────────────────────────
  const handleDownload = async () => {
    try {
      const result = await download.mutate({
        investigationId: report.investigationId,
        reportId: report.reportId,
      });
      if (result.url) {
        const a = document.createElement("a");
        a.href = result.url;
        a.download = result.filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(result.url);
      }
    } catch {
      // surfaced via download.error
    }
  };

  return (
    <Card className="glass border-border/60 overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-2 p-4 border-b border-border/60">
        <FileText className="h-4 w-4 text-primary" aria-hidden="true" />
        <div className="min-w-0 flex-1">
          <div className="font-medium text-sm truncate">
            {investigation?.name ?? report.investigationId}
          </div>
          <div className="text-[11px] text-muted-foreground font-mono">
            {report.investigationId} · Generated {fmtDate(report.createdAt)}
          </div>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <span className={cn("text-[10px] px-2 py-0.5 rounded-full font-medium", statusColor[report.status])}>
            {statusLabel[report.status]}
          </span>
          <Button
            size="sm"
            disabled={!isReady || download.isPending}
            onClick={handleDownload}
            className="bg-gradient-to-r from-primary to-accent text-primary-foreground gap-1"
          >
            {download.isPending ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
            ) : (
              <Download className="h-3.5 w-3.5" aria-hidden="true" />
            )}
            {download.isPending ? "Preparing…" : "Download PDF"}
          </Button>
        </div>
      </div>

      {/* Download error */}
      {download.error && (
        <div className="flex items-center gap-2 px-4 py-2 bg-destructive/10 text-destructive text-xs">
          <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
          {download.error.message}
        </div>
      )}

      {/* Mock report preview */}
      <div className="p-6 bg-[oklch(0.11_0.015_260)] min-h-[520px]">
        <div className="max-w-2xl mx-auto bg-white text-black rounded-md p-10 shadow-2xl">
          <div className="flex items-center justify-between border-b pb-4">
            <div>
              <div className="text-xs uppercase tracking-widest text-slate-500">Confidential — TLP:AMBER</div>
              <div className="mt-1 text-xl font-bold">{investigation?.name ?? "Investigation Report"}</div>
            </div>
            <div className="text-right">
              <div className="text-[10px] uppercase tracking-widest text-slate-400">AXIOM Intel</div>
              <div className="text-[10px] font-mono text-slate-500">{report.investigationId}</div>
            </div>
          </div>

          <div className="mt-6 space-y-4 text-xs text-slate-700">
            <div>
              <div className="text-[10px] uppercase tracking-widest text-slate-400 mb-1">Report Status</div>
              <div className="flex items-center gap-2">
                <ReportStatusIcon status={report.status} />
                <span className="font-medium">{statusLabel[report.status]}</span>
                <span className="text-slate-400 ml-auto">Generated {fmtDate(report.createdAt)}</span>
              </div>
            </div>

            {investigation && (
              <>
                <div className="grid grid-cols-3 gap-3">
                  {[
                    ["Target", investigation.target || "—"],
                    ["Status", investigation.status],
                    ["Severity", investigation.severity],
                  ].map(([l, v]) => (
                    <div key={l} className="border border-slate-200 rounded p-2">
                      <div className="text-[9px] uppercase text-slate-400">{l}</div>
                      <div className="font-bold text-slate-900 capitalize">{v}</div>
                    </div>
                  ))}
                </div>

                <div>
                  <div className="text-[10px] uppercase tracking-widest text-slate-400 mb-1">Investigation Details</div>
                  <p>
                    Investigation <strong>{investigation.id}</strong> was created on{" "}
                    {fmtDate(investigation.createdAt)} and targets{" "}
                    <code className="bg-slate-100 px-1 rounded">{investigation.target || "—"}</code>.
                    {investigation.tags.length > 0 && (
                      <> Tagged: {investigation.tags.map((t) => `#${t}`).join(", ")}.</>
                    )}
                  </p>
                </div>
              </>
            )}

            {isPending && (
              <div className="border-t pt-4 text-center text-slate-400">
                <Loader2 className="h-5 w-5 animate-spin mx-auto mb-2" />
                <p>Report is being generated — polling for status…</p>
              </div>
            )}

            {isFailed && (
              <div className="border-t pt-4 text-center text-red-400">
                <XCircle className="h-5 w-5 mx-auto mb-2" />
                <p>Report generation failed. Please try generating again.</p>
              </div>
            )}

            <div className="border-t pt-3 text-[9px] text-slate-400">
              Generated {fmtDate(report.createdAt)} · AXIOM OSINT Platform
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}

// ─── Reports page ─────────────────────────────────────────────────────────────

function ReportsPage() {
  const invRes = useInvestigations();
  const generate = useGenerateReport();
  const { reports, addReport, updateReport } = useSessionReports();
  const [selectedReport, setSelectedReport] = useState<SessionReport | null>(null);
  const [selectedInvId, setSelectedInvId] = useState<string>("");

  const investigations = invRes.data ?? [];
  const selectedInv = investigations.find((i) => i.id === selectedInvId);

  // Keep selectedReport in sync when the same report's status is updated
  const handleStatusUpdate = useCallback(
    (reportId: string, status: SessionReport["status"]) => {
      updateReport(reportId, { status });
      setSelectedReport((prev) =>
        prev?.reportId === reportId ? { ...prev, status } : prev
      );
    },
    [updateReport]
  );

  const handleGenerate = async () => {
    if (!selectedInvId || !selectedInv) return;
    try {
      const result = await generate.mutate(selectedInvId);
      const mapped: SessionReport["status"] =
        result.status === "ready"
          ? "ready"
          : result.status === "failed"
          ? "failed"
          : result.status === "generating"
          ? "generating"
          : "queued";

      const newReport: SessionReport = {
        reportId: result.reportId,
        investigationId: result.investigationId,
        investigationName: selectedInv.name,
        status: mapped,
        createdAt: result.createdAt,
      };
      addReport(newReport);
      setSelectedReport(newReport);
    } catch {
      // surfaced via generate.error
    }
  };

  // Sync selectedReport with latest version from the list (for status updates)
  const liveSelectedReport = selectedReport
    ? (reports.find((r) => r.reportId === selectedReport.reportId) ?? selectedReport)
    : null;

  return (
    <AppShell
      title="Reports"
      subtitle="Evidence-grade exports and generated summaries"
      actions={
        <Button
          onClick={handleGenerate}
          disabled={!selectedInvId || generate.isPending}
          className="bg-gradient-to-r from-primary to-accent text-primary-foreground gap-2"
        >
          {generate.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          ) : (
            <Plus className="h-4 w-4" aria-hidden="true" />
          )}
          {generate.isPending ? "Generating…" : "Generate report"}
        </Button>
      }
    >
      <div className="grid grid-cols-1 xl:grid-cols-[420px_1fr] gap-4">
        {/* Left: report history */}
        <div className="space-y-3">
          {/* Generate card */}
          <Card className="glass p-4 border-border/60 border-dashed">
            <div className="flex items-center gap-3 mb-3">
              <div className="h-10 w-10 rounded-lg bg-gradient-to-br from-primary to-accent grid place-items-center shrink-0" aria-hidden="true">
                <Sparkles className="h-4 w-4 text-primary-foreground" />
              </div>
              <div className="flex-1">
                <div className="font-medium text-sm">Generate a new PDF report</div>
                <div className="text-xs text-muted-foreground">Select an investigation then click Generate.</div>
              </div>
            </div>

            {/* Investigation picker */}
            <AsyncBoundary resource={invRes}>
              {(investigations) => (
                <Select value={selectedInvId} onValueChange={setSelectedInvId}>
                  <SelectTrigger className="w-full bg-surface/60 text-sm" aria-label="Select investigation to report on">
                    <SelectValue placeholder="Choose investigation…" />
                  </SelectTrigger>
                  <SelectContent>
                    {investigations.map((inv) => (
                      <SelectItem key={inv.id} value={inv.id}>
                        {inv.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            </AsyncBoundary>

            {generate.error && (
              <p className="mt-2 text-xs text-destructive flex items-center gap-1">
                <AlertTriangle className="h-3.5 w-3.5 shrink-0" /> {generate.error.message}
              </p>
            )}
          </Card>

          {/* Session report list */}
          {reports.length === 0 ? (
            <EmptyState
              title="No reports generated yet."
              description="Select an investigation and click Generate to create your first report."
            />
          ) : (
            <div className="space-y-2">
              {reports.map((r) => (
                <ReportListItem
                  key={r.reportId}
                  report={r}
                  active={liveSelectedReport?.reportId === r.reportId}
                  onSelect={setSelectedReport}
                />
              ))}
            </div>
          )}
        </div>

        {/* Right: preview */}
        {liveSelectedReport ? (
          <ReportPreview
            key={liveSelectedReport.reportId}
            report={liveSelectedReport}
            investigation={investigations.find((i) => i.id === liveSelectedReport.investigationId)}
            onStatusUpdate={handleStatusUpdate}
          />
        ) : (
          <Card className="glass border-border/60 min-h-[400px] grid place-items-center">
            <EmptyState
              title="Select a report to preview"
              description="Generate a report or choose one from the list on the left."
            />
          </Card>
        )}
      </div>
    </AppShell>
  );
}
