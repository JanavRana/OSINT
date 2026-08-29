import { cn } from "@/lib/utils";
import type { ConnectorRunStatus, InvestigationStatus, Severity } from "@/types/domain";

type BadgeStatus = InvestigationStatus | ConnectorRunStatus;

export function StatusBadge({ status }: { status: BadgeStatus }) {
  const map: Record<string, { label: string; cls: string; dot: string }> = {
    active:    { label: "ACTIVE",    cls: "bg-primary/10 text-primary border-primary/40",    dot: "bg-primary" },
    completed: { label: "COMPLETED", cls: "bg-success/10 text-success border-success/40",    dot: "bg-success" },
    pending:   { label: "PENDING",   cls: "bg-warning/10 text-warning border-warning/40",    dot: "bg-warning" },
    failed:    { label: "FAILED",    cls: "bg-destructive/10 text-destructive border-destructive/40", dot: "bg-destructive" },
    success:   { label: "SUCCESS",   cls: "bg-success/10 text-success border-success/40",    dot: "bg-success" },
    running:   { label: "RUNNING",   cls: "bg-primary/10 text-primary border-primary/40",    dot: "bg-primary" },
    queued:    { label: "QUEUED",    cls: "bg-muted text-muted-foreground border-border",    dot: "bg-muted-foreground" },
  };
  const m = map[status] ?? { label: String(status).toUpperCase(), cls: "bg-muted text-muted-foreground border-border", dot: "bg-muted-foreground" };
  return (
    <span className={cn("inline-flex items-center gap-1.5 rounded-sm border px-2 py-0.5 text-[10px] font-mono font-semibold tracking-wider", m.cls)}>
      <span className={cn("h-1.5 w-1.5 rounded-full shrink-0", m.dot)} />
      {m.label}
    </span>
  );
}

export function SeverityBadge({ severity }: { severity: Severity }) {
  const map: Record<Severity, string> = {
    critical: "bg-destructive/15 text-destructive border-destructive/40",
    high:     "bg-orange-500/15 text-orange-400 border-orange-500/40",
    medium:   "bg-warning/15 text-warning border-warning/40",
    low:      "bg-muted text-muted-foreground border-border",
  };
  return (
    <span className={cn("inline-flex items-center rounded-sm border px-2 py-0.5 text-[9px] font-mono font-bold uppercase tracking-widest", map[severity])}>
      {severity}
    </span>
  );
}

