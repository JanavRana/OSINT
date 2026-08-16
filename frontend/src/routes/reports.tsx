import { createFileRoute } from "@tanstack/react-router";
import { useCallback, useEffect, useRef, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  FileText, Download, Clock, CheckCircle2,
  XCircle, Loader2, AlertTriangle, FileDown, Shield, ChevronRight,
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
  head: () => ({ meta: [{ title: "Reports — IntelWeave" }] }),
  component: ReportsPage,
});

// ─── Status icon ──────────────────────────────────────────────────────────────

function ReportStatusIcon({ status }: { status: SessionReport["status"] }) {
  switch (status) {
    case "ready":
      return <CheckCircle2 className="h-4 w-4 text-emerald-400" />;
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
  ready: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
  failed: "text-destructive bg-destructive/10 border-destructive/20",
  generating: "text-primary bg-primary/10 border-primary/20",
  queued: "text-muted-foreground bg-surface-2 border-border/40",
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
        "w-full text-left rounded-md p-3 border transition-colors focus-visible:outline-none font-mono text-xs",
        active
          ? "border-primary/50 bg-primary/10 text-foreground"
          : "border-border/60 hover:border-border bg-surface-2/60 text-muted-foreground hover:text-foreground"
      )}
    >
      <div className="flex items-start gap-3">
        <div className="h-8 w-8 rounded bg-primary/10 text-primary grid place-items-center shrink-0 mt-0.5" aria-hidden="true">
          <FileText className="h-4 w-4" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="font-bold text-foreground truncate">
            {report.investigationName}
          </div>
          <div className="text-[10px] text-muted-foreground font-mono mt-0.5">
            {report.investigationId} · {fmtDate(report.createdAt)}
          </div>
          <div className="mt-2 flex items-center gap-2 text-[10px]">
            <ReportStatusIcon status={report.status} />
            <span className={cn("px-1.5 py-0.5 rounded border text-[9px] font-bold uppercase", statusColor[report.status])}>
              {statusLabel[report.status]}
            </span>
            <span className="text-muted-foreground">PDF</span>
          </div>
        </div>
        <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0 self-center" aria-hidden="true" />
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
      const result = await generate.mutate(report.investigationId);
      const newStatus: SessionReport["status"] =
        result.status === "ready" || (result.status as string) === "completed"
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
      pollingRef.current = setInterval(pollStatus, 3000);
    } else {
      stopPolling();
    }
    return stopPolling;
  }, [isPending, pollStatus, stopPolling]);

  // ── Download PDF ────────────────────────────────────────────────────────────
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
    <Card className="border-border bg-surface rounded-md overflow-hidden">
      {/* Header */}
      <div className="p-3 border-b border-border bg-surface-2/40 flex items-center justify-between font-mono text-xs">
        <div className="flex items-center gap-2 min-w-0">
          <FileText className="h-4 w-4 text-primary shrink-0" aria-hidden="true" />
          <span className="font-bold text-foreground truncate">
            {investigation?.name ?? report.investigationId}
          </span>
          <span className="text-[10px] text-muted-foreground hidden sm:inline">
            ({report.investigationId})
          </span>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className={cn("text-[9px] px-2 py-0.5 rounded border font-bold uppercase", statusColor[report.status])}>
            {statusLabel[report.status]}
          </span>
          <Button
            size="sm"
            disabled={!isReady || download.isPending}
            onClick={handleDownload}
            className="bg-primary text-primary-foreground hover:bg-primary/90 text-xs font-mono gap-1.5 h-7 rounded-sm"
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
        <div className="flex items-center gap-2 px-4 py-2 bg-destructive/10 text-destructive text-xs border-b border-border">
          <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
          {download.error.message}
        </div>
      )}

      {/* Flat Report Details & Metadata Preview */}
      <div className="p-6 space-y-6 font-mono text-xs">
        <div className="p-4 bg-surface-2/60 border border-border/80 rounded-md space-y-3">
          <div className="flex items-center justify-between border-b border-border/60 pb-3">
            <div>
              <div className="text-[10px] uppercase tracking-widest text-muted-foreground">Classification: TLP:AMBER</div>
              <h2 className="text-sm font-bold text-foreground mt-0.5">{investigation?.name ?? "OSINT Intelligence Dossier"}</h2>
            </div>
            <div className="text-right">
              <div className="text-[10px] uppercase tracking-widest text-muted-foreground">INTELWEAVE OSINT Engine</div>
              <div className="text-[10px] font-mono text-primary font-bold mt-0.5">{report.investigationId}</div>
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs pt-1">
            <div className="p-2 bg-surface border border-border/60 rounded-sm">
              <div className="text-[9px] uppercase text-muted-foreground">Target</div>
              <div className="font-bold text-foreground mt-0.5 truncate">{investigation?.target || "N/A"}</div>
            </div>
            <div className="p-2 bg-surface border border-border/60 rounded-sm">
              <div className="text-[9px] uppercase text-muted-foreground">Status</div>
              <div className="font-bold text-foreground mt-0.5 uppercase">{investigation?.status || "Active"}</div>
            </div>
            <div className="p-2 bg-surface border border-border/60 rounded-sm">
              <div className="text-[9px] uppercase text-muted-foreground">Severity</div>
              <div className="font-bold text-foreground mt-0.5 uppercase">{investigation?.severity || "Medium"}</div>
            </div>
            <div className="p-2 bg-surface border border-border/60 rounded-sm">
              <div className="text-[9px] uppercase text-muted-foreground">Generated At</div>
              <div className="font-bold text-foreground mt-0.5">{fmtDate(report.createdAt)}</div>
            </div>
          </div>

          <div className="text-xs text-muted-foreground pt-1 space-y-1.5">
            <div className="text-[10px] font-bold text-foreground uppercase tracking-wider">Report Format & Content</div>
            <p>
              This export provides an evidence-grade PDF document containing full intelligence data for case <code className="text-foreground bg-surface px-1 py-0.5 rounded border border-border/40">{report.investigationId}</code>.
            </p>
            <ul className="list-disc pl-4 space-y-1 text-[11px]">
              <li>Executive Overview & Risk Summary</li>
              <li>Normalized Extracted Entity Identifiers with Confidence Scores</li>
              <li>Connector Execution Logs & Duration Timestamps</li>
              <li>Chronological Event Timeline</li>
              <li>Investigator Attestation & SHA256 Verification Digest</li>
            </ul>
          </div>
        </div>

        {/* Action footer */}
        <div className="flex items-center justify-between p-4 bg-surface-2/40 border border-border/60 rounded-md">
          <div className="flex items-center gap-2 text-muted-foreground text-[11px]">
            <Shield className="h-4 w-4 text-primary shrink-0" />
            <span>Click Download PDF to save the complete, formatted dossier.</span>
          </div>
          <Button
            size="sm"
            disabled={!isReady || download.isPending}
            onClick={handleDownload}
            className="bg-primary text-primary-foreground hover:bg-primary/90 text-xs font-mono gap-1.5 h-8 rounded-sm"
          >
            {download.isPending ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
            ) : (
              <Download className="h-3.5 w-3.5" aria-hidden="true" />
            )}
            {download.isPending ? "Generating PDF…" : "Download PDF Report"}
          </Button>
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
        result.status === "ready" || (result.status as string) === "completed"
          ? "ready"
          : result.status === "failed"
          ? "failed"
          : result.status === "generating"
          ? "generating"
          : "ready";

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

  // Sync selectedReport with latest version from the list
  const liveSelectedReport = selectedReport
    ? (reports.find((r) => r.reportId === selectedReport.reportId) ?? selectedReport)
    : null;

  return (
    <AppShell
      title="Reports"
      subtitle="Evidence-grade PDF exports and generated summaries"
    >
      <div className="grid grid-cols-1 xl:grid-cols-[340px_1fr] gap-3">
        {/* Left: Controls sidebar & report history */}
        <div className="space-y-3">
          {/* Generate card */}
          <Card className="p-4 border-border bg-surface rounded-md space-y-3 font-mono text-xs">
            <h3 className="font-display text-xs font-bold uppercase tracking-wider text-foreground pb-2 border-b border-border/60">
              Generate Report
            </h3>

            {/* Target investigation */}
            <div>
              <label className="text-[10px] text-muted-foreground uppercase">Target Investigation</label>
              <AsyncBoundary resource={invRes}>
                {(investigations) => (
                  <Select value={selectedInvId} onValueChange={setSelectedInvId}>
                    <SelectTrigger className="mt-1 bg-surface-2 border-border text-xs h-8">
                      <SelectValue placeholder="Choose case…" />
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
            </div>

            {generate.error && (
              <p className="mt-1 text-[11px] text-destructive flex items-center gap-1">
                <AlertTriangle className="h-3.5 w-3.5 shrink-0" /> {generate.error.message}
              </p>
            )}

            <Button
              onClick={handleGenerate}
              disabled={!selectedInvId || generate.isPending}
              className="w-full bg-primary text-primary-foreground hover:bg-primary/90 text-xs font-mono gap-1.5 h-8 rounded-sm mt-1"
            >
              {generate.isPending ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
              ) : (
                <FileDown className="h-3.5 w-3.5" aria-hidden="true" />
              )}
              {generate.isPending ? "Generating PDF…" : "Generate PDF Report"}
            </Button>
          </Card>

          {/* Session report list */}
          {reports.length > 0 && (
            <Card className="p-3 border-border bg-surface rounded-md font-mono text-xs space-y-2">
              <h3 className="font-display text-xs font-bold uppercase tracking-wider text-foreground pb-2 border-b border-border/60 mb-2">
                Generated Dossiers
              </h3>
              <div className="space-y-1.5 max-h-[480px] overflow-y-auto pr-1">
                {reports.map((r) => (
                  <ReportListItem
                    key={r.reportId}
                    report={r}
                    active={liveSelectedReport?.reportId === r.reportId}
                    onSelect={setSelectedReport}
                  />
                ))}
              </div>
            </Card>
          )}
        </div>

        {/* Right: preview / details */}
        {liveSelectedReport ? (
          <ReportPreview
            key={liveSelectedReport.reportId}
            report={liveSelectedReport}
            investigation={investigations.find((i) => i.id === liveSelectedReport.investigationId)}
            onStatusUpdate={handleStatusUpdate}
          />
        ) : (
          <Card className="border-border bg-surface rounded-md min-h-[400px] grid place-items-center p-6">
            <EmptyState
              title="Select an investigation"
              description="Choose a case on the left and click Generate PDF Report to compile and download your evidence dossier."
            />
          </Card>
        )}
      </div>
    </AppShell>
  );
}
