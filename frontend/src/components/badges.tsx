import { cn } from "@/lib/utils";
import type { ConnectorRunStatus, InvestigationStatus, Severity } from "@/types/domain";

type BadgeStatus = InvestigationStatus | ConnectorRunStatus;

export function StatusBadge({ status }: { status: BadgeStatus }) {
  const map: Record<string, {
    label: string;
    cls: string;
    dot: string;
    animate?: boolean;
    glow?: string;
  }> = {
    active:    {
      label: "ACTIVE",
      cls: "bg-primary/10 text-primary border-primary/40",
      dot: "bg-primary",
      animate: true,
      glow: "shadow-[0_0_8px_var(--color-primary,#60a5fa)]/30",
    },
    completed: {
      label: "COMPLETED",
      cls: "bg-success/10 text-success border-success/40",
      dot: "bg-success",
    },
    pending:   {
      label: "PENDING",
      cls: "bg-warning/10 text-warning border-warning/40",
      dot: "bg-warning",
      animate: true,
    },
    failed:    {
      label: "FAILED",
      cls: "bg-destructive/10 text-destructive border-destructive/40",
      dot: "bg-destructive",
    },
    success:   {
      label: "SUCCESS",
      cls: "bg-success/10 text-success border-success/40",
      dot: "bg-success",
    },
    running:   {
      label: "RUNNING",
      cls: "bg-primary/10 text-primary border-primary/40",
      dot: "bg-primary",
      animate: true,
      glow: "shadow-[0_0_8px_var(--color-primary,#60a5fa)]/30",
    },
    queued:    {
      label: "QUEUED",
      cls: "bg-muted/80 text-muted-foreground border-border",
      dot: "bg-muted-foreground/60",
    },
  };
  const m = map[status] ?? {
    label: String(status).toUpperCase(),
    cls: "bg-muted text-muted-foreground border-border",
    dot: "bg-muted-foreground",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-sm border px-2 py-0.5",
        "text-[10px] font-mono font-semibold tracking-wider transition-all duration-300",
        m.cls,
        m.glow,
      )}
    >
      <span
        className={cn(
          "h-1.5 w-1.5 rounded-full shrink-0",
          m.dot,
          m.animate && "animate-pulse-dot",
        )}
      />
      {m.label}
    </span>
  );
}

export function SeverityBadge({ severity }: { severity: Severity }) {
  const map: Record<Severity, { cls: string; dot: string }> = {
    critical: {
      cls: "bg-destructive/15 text-destructive border-destructive/50",
      dot: "bg-destructive",
    },
    high: {
      cls: "bg-orange-500/15 text-orange-400 border-orange-500/40",
      dot: "bg-orange-400",
    },
    medium: {
      cls: "bg-warning/15 text-warning border-warning/40",
      dot: "bg-warning",
    },
    low: {
      cls: "bg-muted/80 text-muted-foreground border-border",
      dot: "bg-muted-foreground/50",
    },
  };
  const m = map[severity];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-sm border px-2 py-0.5",
        "text-[9px] font-mono font-bold uppercase tracking-widest",
        m.cls,
      )}
    >
      <span className={cn("h-1 w-1 rounded-full shrink-0", m.dot)} />
      {severity}
    </span>
  );
}

