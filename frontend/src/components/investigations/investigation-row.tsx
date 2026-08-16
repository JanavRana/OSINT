import { Link } from "@tanstack/react-router";
import { Progress } from "@/components/ui/progress";
import { SeverityBadge, StatusBadge } from "@/components/badges";
import type { Investigation } from "@/types/domain";

export function InvestigationRow({ investigation }: { investigation: Investigation }) {
  const inv = investigation;
  return (
    <Link
      to="/investigations/$id"
      params={{ id: inv.id }}
      className="flex items-center gap-3 p-2.5 rounded-sm border border-border/60 bg-surface-2/40 hover:bg-surface-3 transition focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary"
    >
      <div className="h-7 px-2 rounded-sm bg-surface-3 border border-border grid place-items-center shrink-0 font-mono text-[10px] font-bold text-primary">
        {inv.id.split("-")[1]}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-medium text-xs text-foreground truncate">{inv.name}</span>
          <SeverityBadge severity={inv.severity} />
        </div>
        <div className="text-[11px] text-muted-foreground font-mono truncate">{inv.target}</div>
      </div>
      <div className="hidden md:block w-28 text-right">
        <Progress value={inv.progress} className="h-1 bg-surface-3" />
        <div className="text-[9px] font-mono text-muted-foreground mt-1">
          {inv.progress}% · {inv.identifiers} ids
        </div>
      </div>
      <StatusBadge status={inv.status} />
    </Link>
  );
}

