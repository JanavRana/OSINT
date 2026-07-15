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
      className="flex items-center gap-4 p-3 rounded-xl border border-transparent hover:border-border/60 hover:bg-white/[0.03] transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
    >
      <div className="h-10 w-10 rounded-lg bg-gradient-to-br from-primary/20 to-accent/20 grid place-items-center shrink-0">
        <span className="text-[10px] font-mono text-primary">{inv.id.split("-")[1]}</span>
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-medium truncate">{inv.name}</span>
          <SeverityBadge severity={inv.severity} />
        </div>
        <div className="text-xs text-muted-foreground font-mono truncate">{inv.target}</div>
      </div>
      <div className="hidden md:block w-32">
        <Progress value={inv.progress} className="h-1.5" />
        <div className="text-[10px] text-muted-foreground mt-1">
          {inv.progress}% • {inv.identifiers} ids
        </div>
      </div>
      <StatusBadge status={inv.status} />
    </Link>
  );
}
