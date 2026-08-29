import { Activity, AlertTriangle, ArrowDownRight, ArrowUpRight, Fingerprint, TrendingUp, Zap } from "lucide-react";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { DashboardStat, StatTone } from "@/types/domain";

const toneTextMap: Record<StatTone, string> = {
  cyan: "text-primary",
  violet: "text-accent",
  warning: "text-warning",
  danger: "text-destructive",
};

const iconForTone: Record<StatTone, typeof Activity> = {
  cyan: Activity,
  violet: Fingerprint,
  warning: Zap,
  danger: AlertTriangle,
};

export function StatCard({ stat }: { stat: DashboardStat }) {
  const Icon = iconForTone[stat.tone];
  return (
    <Card className="p-3.5 border-border bg-surface rounded-md">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="text-[10px] uppercase font-mono tracking-wider text-muted-foreground">
            {stat.label}
          </div>
          <div className="mt-1 text-xl font-mono font-bold tracking-tight text-foreground">
            {stat.value}
          </div>
        </div>
        <div
          className={cn(
            "h-7 w-7 rounded-sm grid place-items-center bg-surface-2 border border-border shrink-0",
            toneTextMap[stat.tone],
          )}
          aria-hidden="true"
        >
          <Icon className="h-3.5 w-3.5" />
        </div>
      </div>
      <div className="mt-2.5 flex items-center gap-1.5 text-[11px] text-muted-foreground font-mono">
        {stat.trend === "up" && (
          <ArrowUpRight className="h-3 w-3 text-success shrink-0" aria-hidden="true" />
        )}
        {stat.trend === "down" && (
          <ArrowDownRight className="h-3 w-3 text-success shrink-0" aria-hidden="true" />
        )}
        {stat.trend === "warn" && (
          <TrendingUp className="h-3 w-3 text-warning shrink-0" aria-hidden="true" />
        )}
        <span className="truncate">{stat.delta}</span>
      </div>
    </Card>
  );
}

