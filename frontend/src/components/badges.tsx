import { cn } from "@/lib/utils";
import type { ConnectorRunStatus, InvestigationStatus, Severity } from "@/types/domain";

type BadgeStatus = InvestigationStatus | ConnectorRunStatus;

export function StatusBadge({ status }: { status: BadgeStatus }) {
  const map: Record<string, { label: string; cls: string; dot: string }> = {
    active:    { label: "Active",    cls: "bg-primary/10 text-primary border-primary/30",    dot: "bg-primary" },
    completed: { label: "Completed", cls: "bg-success/10 text-success border-success/30",    dot: "bg-success" },
    pending:   { label: "Pending",   cls: "bg-warning/10 text-warning border-warning/30",    dot: "bg-warning" },
    failed:    { label: "Failed",    cls: "bg-destructive/10 text-destructive border-destructive/30", dot: "bg-destructive" },
    success:   { label: "Success",   cls: "bg-success/10 text-success border-success/30",    dot: "bg-success" },
    running:   { label: "Running",   cls: "bg-primary/10 text-primary border-primary/30",    dot: "bg-primary" },
    queued:    { label: "Queued",    cls: "bg-muted text-muted-foreground border-border",    dot: "bg-muted-foreground" },
  };
  const m = map[status];
  return (
    <span className={cn("inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-medium", m.cls)}>
      <span className={cn("h-1.5 w-1.5 rounded-full", m.dot, (status === "active" || status === "running") && "pulse-ring")} />
      {m.label}
    </span>
  );
}

export function SeverityBadge({ severity }: { severity: Severity }) {
  const map: Record<Severity, string> = {
    critical: "bg-destructive/10 text-destructive border-destructive/30",
    high:     "bg-orange-500/10 text-orange-400 border-orange-500/30",
    medium:   "bg-warning/10 text-warning border-warning/30",
    low:      "bg-muted text-muted-foreground border-border",
  };
  return (
    <span className={cn("inline-flex items-center rounded-md border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider", map[severity])}>
      {severity}
    </span>
  );
}
