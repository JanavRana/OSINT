import { Activity, AlertTriangle, ArrowDownRight, ArrowUpRight, Fingerprint, TrendingUp, Zap } from "lucide-react";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { DashboardStat, StatTone } from "@/types/domain";

const toneMap: Record<StatTone, string> = {
  cyan: "from-primary/20 to-primary/0 text-primary",
  violet: "from-accent/20 to-accent/0 text-accent",
  warning: "from-warning/20 to-warning/0 text-warning",
  danger: "from-destructive/20 to-destructive/0 text-destructive",
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
    <Card className="glass relative overflow-hidden p-5 border-border/60">
      <div
        aria-hidden="true"
        className={cn(
          "absolute -top-16 -right-16 h-40 w-40 rounded-full blur-3xl bg-gradient-radial",
          toneMap[stat.tone],
        )}
      />
      <div className="relative flex items-start justify-between">
        <div>
          <div className="text-xs uppercase tracking-wider text-muted-foreground">
            {stat.label}
          </div>
          <div className="mt-2 text-3xl font-display font-bold">{stat.value}</div>
        </div>
        <div
          className={cn(
            "h-9 w-9 rounded-lg grid place-items-center bg-gradient-to-br",
            toneMap[stat.tone],
          )}
          aria-hidden="true"
        >
          <Icon className="h-4 w-4" />
        </div>
      </div>
      <div className="relative mt-3 flex items-center gap-1 text-xs text-muted-foreground">
        {stat.trend === "up" && (
          <ArrowUpRight className="h-3 w-3 text-success" aria-hidden="true" />
        )}
        {stat.trend === "down" && (
          <ArrowDownRight className="h-3 w-3 text-success" aria-hidden="true" />
        )}
        {stat.trend === "warn" && (
          <TrendingUp className="h-3 w-3 text-warning" aria-hidden="true" />
        )}
        <span>{stat.delta}</span>
      </div>
    </Card>
  );
}
