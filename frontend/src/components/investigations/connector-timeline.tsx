/**
 * connector-timeline.tsx
 *
 * Renders ExecutionConnectorResult[] as a vertical timeline stepper.
 * Shows each connector's execution in order with start/end times,
 * status indicator, and error messages.
 */

import { CheckCircle2, XCircle, Loader2, Clock3 } from "lucide-react";
import { cn } from "@/lib/utils";
import { fmtDate } from "@/lib/format";
import type { ExecutionConnectorResult } from "@/types/domain";

const statusConfig = {
  success: {
    icon: CheckCircle2,
    color: "text-success",
    bg: "bg-success/15",
    dot: "bg-success",
    label: "Succeeded",
  },
  succeeded: {
    icon: CheckCircle2,
    color: "text-success",
    bg: "bg-success/15",
    dot: "bg-success",
    label: "Succeeded",
  },
  failed: {
    icon: XCircle,
    color: "text-destructive",
    bg: "bg-destructive/15",
    dot: "bg-destructive",
    label: "Failed",
  },
  running: {
    icon: Loader2,
    color: "text-primary",
    bg: "bg-primary/15",
    dot: "bg-primary",
    label: "Running",
  },
  queued: {
    icon: Clock3,
    color: "text-muted-foreground",
    bg: "bg-white/5",
    dot: "bg-muted-foreground",
    label: "Queued",
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
      <p className="text-sm text-muted-foreground py-4">
        No connector results recorded.
      </p>
    );
  }

  return (
    <div className={cn("relative", className)}>
      {/* Vertical line */}
      <div
        className="absolute left-4 top-4 bottom-4 w-px bg-border/60"
        aria-hidden="true"
      />
      <ol className="space-y-1" aria-label="Connector execution timeline">
        {results.map((cr, idx) => {
          const cfg = getStatusConfig(cr.status);
          const Icon = cfg.icon;
          const isLast = idx === results.length - 1;
          return (
            <li key={`${cr.connectorName}-${idx}`} className="relative flex gap-4">
              {/* Dot */}
              <div
                className={cn(
                  "relative z-10 h-8 w-8 shrink-0 rounded-full grid place-items-center border-2 border-background",
                  cfg.bg
                )}
                aria-hidden="true"
              >
                <Icon
                  className={cn(
                    "h-3.5 w-3.5",
                    cfg.color,
                    cr.status === "running" && "animate-spin"
                  )}
                />
              </div>

              {/* Content */}
              <div
                className={cn(
                  "flex-1 rounded-xl p-3 border border-border/40 bg-surface/40 mb-3",
                  cr.status === "failed" && "border-destructive/30 bg-destructive/[0.04]"
                )}
              >
                <div className="flex items-center justify-between gap-2 flex-wrap">
                  <span className="text-sm font-medium capitalize">
                    {cr.connectorName}
                  </span>
                  <div className="flex items-center gap-2">
                    <span
                      className={cn(
                        "text-[10px] uppercase tracking-widest px-2 py-0.5 rounded-full font-medium",
                        cfg.bg,
                        cfg.color
                      )}
                    >
                      {cfg.label}
                    </span>
                    <span className="text-[11px] font-mono text-muted-foreground">
                      {durationLabel(cr.startedAt, cr.finishedAt)}
                    </span>
                  </div>
                </div>

                {/* Timestamps */}
                {(cr.startedAt || cr.finishedAt) && (
                  <div className="mt-1.5 flex gap-4 text-[11px] text-muted-foreground">
                    {cr.startedAt && (
                      <span>
                        Started: <span className="font-mono">{fmtDate(cr.startedAt)}</span>
                      </span>
                    )}
                    {cr.finishedAt && (
                      <span>
                        Finished: <span className="font-mono">{fmtDate(cr.finishedAt)}</span>
                      </span>
                    )}
                  </div>
                )}

                {/* Error message */}
                {cr.errorMessage && (
                  <div className="mt-2 text-xs text-destructive bg-destructive/10 rounded-md px-2 py-1.5 font-mono">
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
