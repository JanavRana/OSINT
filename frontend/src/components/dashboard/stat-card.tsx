import { Activity, AlertTriangle, ArrowDownRight, ArrowUpRight, Fingerprint, TrendingUp, Zap } from "lucide-react";
import { cn } from "@/lib/utils";
import type { DashboardStat, StatTone } from "@/types/domain";

const toneConfig: Record<StatTone, {
  text: string;
  iconBg: string;
  gradient: string;
  accentBar: string;
  glow: string;
}> = {
  cyan: {
    text: "text-primary",
    iconBg: "bg-primary/10 border-primary/30",
    gradient: "from-primary/8 to-transparent",
    accentBar: "linear-gradient(90deg, oklch(0.68 0.18 230 / 0.9), oklch(0.68 0.18 230 / 0.1))",
    glow: "hover:shadow-[0_4px_24px_oklch(0.68_0.18_230_/_0.18)]",
  },
  violet: {
    text: "text-accent",
    iconBg: "bg-accent/10 border-accent/30",
    gradient: "from-accent/8 to-transparent",
    accentBar: "linear-gradient(90deg, oklch(0.65 0.20 285 / 0.9), oklch(0.65 0.20 285 / 0.1))",
    glow: "hover:shadow-[0_4px_24px_oklch(0.65_0.20_285_/_0.18)]",
  },
  warning: {
    text: "text-warning",
    iconBg: "bg-warning/10 border-warning/30",
    gradient: "from-warning/8 to-transparent",
    accentBar: "linear-gradient(90deg, oklch(0.76 0.16 78 / 0.9), oklch(0.76 0.16 78 / 0.1))",
    glow: "hover:shadow-[0_4px_24px_oklch(0.76_0.16_78_/_0.18)]",
  },
  danger: {
    text: "text-destructive",
    iconBg: "bg-destructive/10 border-destructive/30",
    gradient: "from-destructive/8 to-transparent",
    accentBar: "linear-gradient(90deg, oklch(0.60 0.22 25 / 0.9), oklch(0.60 0.22 25 / 0.1))",
    glow: "hover:shadow-[0_4px_24px_oklch(0.60_0.22_25_/_0.18)]",
  },
};

const iconForTone: Record<StatTone, typeof Activity> = {
  cyan: Activity,
  violet: Fingerprint,
  warning: Zap,
  danger: AlertTriangle,
};

export function StatCard({ stat }: { stat: DashboardStat }) {
  const Icon = iconForTone[stat.tone];
  const cfg = toneConfig[stat.tone];

  return (
    <div
      className={cn(
        "relative rounded-md border border-border bg-surface overflow-hidden",
        "transition-all duration-300 hover:-translate-y-0.5 cursor-default",
        "shadow-[var(--shadow-elev)]",
        cfg.glow,
      )}
    >
      {/* Top accent gradient bar */}
      <div
        className="absolute top-0 left-0 right-0 h-0.5"
        style={{ background: cfg.accentBar }}
        aria-hidden="true"
      />
      {/* Tonal gradient layer */}
      <div
        className={cn("absolute inset-0 bg-gradient-to-br", cfg.gradient, "pointer-events-none")}
        aria-hidden="true"
      />

      <div className="relative p-3.5">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <div className="text-[10px] uppercase font-mono tracking-wider text-muted-foreground">
              {stat.label}
            </div>
            <div className="mt-1.5 text-2xl font-mono font-bold tracking-tight text-foreground">
              {stat.value}
            </div>
          </div>
          <div
            className={cn(
              "h-8 w-8 rounded-md grid place-items-center border shrink-0 transition-transform duration-300 group-hover:scale-110",
              cfg.iconBg,
              cfg.text,
            )}
            aria-hidden="true"
          >
            <Icon className="h-4 w-4" />
          </div>
        </div>
        <div className="mt-3 flex items-center gap-1.5 text-[11px] text-muted-foreground font-mono">
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
      </div>
    </div>
  );
}

