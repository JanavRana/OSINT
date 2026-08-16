import { CheckCircle2, XCircle, Loader2, Clock3 } from "lucide-react";
import { cn } from "@/lib/utils";
import { fmtDate } from "@/lib/format";
import type { ExecutionConnectorResult } from "@/types/domain";

const statusConfig = {
  success: {
    icon: CheckCircle2,
    color: "text-success",
    bg: "bg-success/10 border-success/30",
    dot: "bg-success",
    label: "SUCCESS",
  },
  succeeded: {
    icon: CheckCircle2,
    color: "text-success",
    bg: "bg-success/10 border-success/30",
    dot: "bg-success",
    label: "SUCCESS",
  },
  failed: {
    icon: XCircle,
    color: "text-destructive",
    bg: "bg-destructive/10 border-destructive/30",
    dot: "bg-destructive",
    label: "FAILED",
  },
  running: {
    icon: Loader2,
    color: "text-primary",
    bg: "bg-primary/10 border-primary/30",
    dot: "bg-primary",
    label: "RUNNING",
  },
  queued: {
    icon: Clock3,
    color: "text-muted-foreground",
    bg: "bg-surface-2 border-border",
    dot: "bg-muted-foreground",
    label: "QUEUED",
  },
} as const;

function getStatusConfig(status: string) {
  return (
    statusConfig[status as keyof typeof statusConfig] ?? statusConfig.queued
  );
}

function durationLabel(
  startedAt: string | null,
  finishedAt: string | null
): string {
  if (!startedAt || !finishedAt) return "—";
  const diff = new Date(finishedAt).getTime() - new Date(startedAt).getTime();
  if (diff < 1000) return `${diff}ms`;
  return `${(diff / 1000).toFixed(1)}s`;
}

interface ConnectorTimelineProps {
  results: ExecutionConnectorResult[];
  className?: string;
}

export function ConnectorTimeline({ results, className }: ConnectorTimelineProps) {
  if (results.length === 0) {
    return (
      <p className="text-xs font-mono text-muted-foreground py-3">
        No connector results recorded.
      </p>
    );
  }

  return (
    <div className={cn("relative font-mono text-xs", className)}>
      <div
        className="absolute left-3 top-3 bottom-3 w-px bg-border"
        aria-hidden="true"
      />
      <ol className="space-y-2" aria-label="Connector execution timeline">
        {results.map((cr, idx) => {
          const cfg = getStatusConfig(cr.status);
          const Icon = cfg.icon;
          return (
            <li key={`${cr.connectorName}-${idx}`} className="relative flex gap-3">
              {/* Dot */}
              <div
                className={cn(
                  "relative z-10 h-6 w-6 shrink-0 rounded-sm grid place-items-center border bg-surface",
                  cfg.bg
                )}
                aria-hidden="true"
              >
                <Icon
                  className={cn(
                    "h-3 w-3",
                    cfg.color,
                    cr.status === "running" && "animate-spin"
                  )}
                />
              </div>

              {/* Content */}
              <div
                className={cn(
                  "flex-1 rounded-sm p-2.5 border border-border bg-surface-2/60",
                  cr.status === "failed" && "border-destructive/40 bg-destructive/5"
                )}
              >
                <div className="flex items-center justify-between gap-2 flex-wrap">
                  <span className="font-semibold text-foreground font-sans text-xs">
                    {cr.connectorName}
                  </span>
                  <div className="flex items-center gap-2">
                    <span
                      className={cn(
                        "text-[9px] font-bold px-1.5 py-0.5 rounded-sm border",
                        cfg.bg,
                        cfg.color
                      )}
                    >
                      {cfg.label}
                    </span>
                    <span className="text-[10px] text-muted-foreground">
                      {durationLabel(cr.startedAt, cr.finishedAt)}
                    </span>
                  </div>
                </div>

                {/* Timestamps */}
                {(cr.startedAt || cr.finishedAt) && (
                  <div className="mt-1 flex gap-3 text-[10px] text-muted-foreground/80">
                    {cr.startedAt && <span>START: {fmtDate(cr.startedAt)}</span>}
                    {cr.finishedAt && <span>END: {fmtDate(cr.finishedAt)}</span>}
                  </div>
                )}

                {/* Error message */}
                {cr.errorMessage && (
                  <div className="mt-1.5 text-[11px] text-destructive bg-destructive/10 border border-destructive/30 rounded-sm p-1.5">
                    {cr.errorMessage}
                  </div>
                )}
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}

