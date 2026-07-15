import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { FileText, Download, Eye, Plus, Sparkles, ChevronRight } from "lucide-react";
import { AsyncBoundary, EmptyState } from "@/components/states";
import { useDownloadReport, useGenerateReport, useReports } from "@/hooks/use-osint-data";
import { cn } from "@/lib/utils";
import type { Report } from "@/types/domain";

export const Route = createFileRoute("/reports")({
  head: () => ({ meta: [{ title: "Reports — AXIOM OSINT" }] }),
  component: ReportsPage,
});

function ReportListItem({
  report,
  active,
  onSelect,
}: {
  report: Report;
  active: boolean;
  onSelect: (r: Report) => void;
}) {
  const r = report;
  return (
    <button
      onClick={() => onSelect(r)}
      aria-pressed={active}
      className={cn(
        "w-full text-left rounded-xl p-4 border transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40",
        active
          ? "border-primary/50 bg-primary/[0.06] shadow-[0_0_20px_-6px_var(--primary)]"
          : "border-border/60 hover:border-border bg-card/60 glass",
      )}
    >
      <div className="flex items-start gap-3">
        <div
          className={cn(
            "h-10 w-10 rounded-lg grid place-items-center shrink-0",
            r.format === "PDF"
              ? "bg-destructive/15 text-destructive"
              : r.format === "JSON"
                ? "bg-accent/15 text-accent"
                : "bg-primary/15 text-primary",
          )}
          aria-hidden="true"
        >
          <FileText className="h-4 w-4" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="font-medium text-sm truncate">{r.name}</div>
          <div className="text-[11px] text-muted-foreground font-mono mt-0.5">
            {r.investigation} · {r.createdAt}
          </div>
          <div className="mt-2 flex items-center gap-2 text-[10px] text-muted-foreground">
            <span className="px-1.5 py-0.5 rounded bg-white/5 border border-border/60">{r.format}</span>
            <span>{r.pages > 0 ? `${r.pages} pages` : "IOC bundle"}</span>
            <span>·</span>
            <span>{r.size}</span>
          </div>
        </div>
        <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0" aria-hidden="true" />
      </div>
    </button>
  );
}

function ReportPreview({ report }: { report: Report }) {
  const download = useDownloadReport();
  return (
    <Card className="glass border-border/60 overflow-hidden">
      <div className="flex items-center gap-2 p-4 border-b border-border/60">
        <FileText className="h-4 w-4 text-primary" aria-hidden="true" />
        <div className="min-w-0">
          <div className="font-medium text-sm truncate">{report.name}</div>
          <div className="text-[11px] text-muted-foreground font-mono">
            {report.investigation} · {report.createdAt}
          </div>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <Button variant="ghost" size="sm" className="gap-1">
            <Eye className="h-3.5 w-3.5" aria-hidden="true" /> Preview
          </Button>
          <Button
            size="sm"
            disabled={download.isPending}
            onClick={() => download.mutate({ investigationId: report.investigation, reportId: report.id }).catch(() => {})}
            className="bg-gradient-to-r from-primary to-accent text-primary-foreground gap-1"
          >
            <Download className="h-3.5 w-3.5" aria-hidden="true" />
            {download.isPending ? "Preparing…" : "Download"}
          </Button>
        </div>
      </div>


      <div className="p-6 bg-[oklch(0.11_0.015_260)] min-h-[600px]">
        <div className="max-w-2xl mx-auto bg-white text-black rounded-md p-10 shadow-2xl aspect-[8.5/11]">
          <div className="flex items-center justify-between border-b pb-4">
            <div>
              <div className="text-xs uppercase tracking-widest text-slate-500">Confidential — TLP:AMBER</div>
              <div className="mt-1 text-xl font-bold">{report.name}</div>
            </div>
            <div className="text-right">
              <div className="text-[10px] uppercase tracking-widest text-slate-400">AXIOM Intel</div>
              <div className="text-[10px] font-mono text-slate-500">{report.investigation}</div>
            </div>
          </div>
          <div className="mt-6 space-y-4 text-xs text-slate-700">
            <div>
              <div className="text-[10px] uppercase tracking-widest text-slate-400 mb-1">Executive Summary</div>
              <p>Between 2024-11-02 and 2026-07-10 the subject was observed operating across 12 platforms using 3 primary email identities and a linked Ethereum wallet…</p>
            </div>
            <div className="grid grid-cols-3 gap-3">
              {[
                ["Identifiers", "47"],
                ["Connectors", "12"],
                ["Confidence", "86%"],
              ].map(([l, v]) => (
                <div key={l} className="border border-slate-200 rounded p-2">
                  <div className="text-[9px] uppercase text-slate-400">{l}</div>
                  <div className="font-bold text-slate-900">{v}</div>
                </div>
              ))}
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-widest text-slate-400 mb-1">Key Findings</div>
              <ul className="list-disc pl-4 space-y-1">
                <li>Subject wallet interacts with sanctioned mixer service.</li>
                <li>Alias @nullbyte_x cross-verified against 4 platforms.</li>
                <li>Typosquat domain registered within 72h of campaign start.</li>
              </ul>
            </div>
            <div className="border-t pt-3 text-[9px] text-slate-400">
              Page 1 of {report.pages || 1} · Generated {report.createdAt}
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}

function ReportsPage() {
  const resource = useReports();
  const generate = useGenerateReport();
  const [selected, setSelected] = useState<Report | null>(null);

  useEffect(() => {
    if (!selected && resource.data && resource.data.length > 0) {
      setSelected(resource.data[0]);
    }
  }, [resource.data, selected]);

  const generateFor = selected?.investigation;
  async function handleGenerate() {
    if (!generateFor) return;
    try {
      await generate.mutate(generateFor);
      resource.refetch?.();
    } catch {
      /* surfaced via generate.error */
    }
  }

  return (
    <AppShell
      title="Reports"
      subtitle="Evidence-grade exports and generated summaries"
      actions={
        <Button
          onClick={handleGenerate}
          disabled={!generateFor || generate.isPending}
          className="bg-gradient-to-r from-primary to-accent text-primary-foreground gap-2"
        >
          <Plus className="h-4 w-4" aria-hidden="true" />
          {generate.isPending ? "Generating…" : "Generate report"}
        </Button>
      }
    >
      <div className="grid grid-cols-1 xl:grid-cols-[420px_1fr] gap-4">
        {/* Report history */}
        <div className="space-y-3">
          <Card className="glass p-4 border-border/60 border-dashed">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-lg bg-gradient-to-br from-primary to-accent grid place-items-center" aria-hidden="true">
                <Sparkles className="h-4 w-4 text-primary-foreground" />
              </div>
              <div className="flex-1">
                <div className="font-medium text-sm">Generate a new PDF report</div>
                <div className="text-xs text-muted-foreground">Pick a case, template and evidence scope.</div>
              </div>
              <Button size="sm" variant="secondary">Start</Button>
            </div>
          </Card>

          <AsyncBoundary
            resource={resource}
            isEmpty={(l) => l.length === 0}
            empty={<EmptyState title="No reports generated yet." description="Start by generating your first report above." />}
          >
            {(list) => (
              <>
                {list.map((r) => (
                  <ReportListItem
                    key={r.id}
                    report={r}
                    active={selected?.id === r.id}
                    onSelect={setSelected}
                  />
                ))}
              </>
            )}
          </AsyncBoundary>
        </div>

        {/* Preview */}
        {selected ? (
          <ReportPreview report={selected} />
        ) : (
          <Card className="glass border-border/60 min-h-[400px] grid place-items-center">
            <EmptyState
              title="Select a report to preview"
              description="Choose one from the list on the left to view its contents."
            />
          </Card>
        )}
      </div>
    </AppShell>
  );
}
