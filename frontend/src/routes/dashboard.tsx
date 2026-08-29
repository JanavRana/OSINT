import { createFileRoute, Link, redirect } from "@tanstack/react-router";
import { isAuthenticated } from "@/lib/auth";
import { AppShell } from "@/components/app-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Plus, Fingerprint, Network, FileText,
  CheckCircle2, XCircle, Clock3, Activity,
  Zap, TrendingUp,
} from "lucide-react";
import { AsyncBoundary, EmptyState } from "@/components/states";
import { StatCard } from "@/components/dashboard/stat-card";
import { SectionCard, ViewAllLink } from "@/components/section-card";
import { InvestigationRow } from "@/components/investigations/investigation-row";
import { TimelineFeedItem } from "@/components/timeline/timeline-feed-item";
import { StatusBadge } from "@/components/badges";
import {
  useDashboardStats,
  useInvestigations,
  useTimeline,
  useConnectors,
} from "@/hooks/use-osint-data";
import { cn } from "@/lib/utils";
import { fmtDate } from "@/lib/format";
import type { Investigation } from "@/types/domain";

export const Route = createFileRoute("/dashboard")({
  beforeLoad: () => {
    if (!isAuthenticated()) throw redirect({ to: "/auth" });
  },
  head: () => ({
    meta: [
      { title: "Dashboard — IntelWeave" },
      { name: "description", content: "Overview of active investigations, connector health, and recent intelligence events." },
    ],
  }),
  component: Dashboard,
});

const quickActions = [
  { icon: Plus, label: "New Case", to: "/investigations/new" as const, tone: "primary" as const },
  { icon: Fingerprint, label: "Identity", to: "/identity" as const, tone: "accent" as const },
  { icon: Network, label: "Graph View", to: "/graph" as const, tone: "primary" as const },
  { icon: FileText, label: "Reports", to: "/reports" as const, tone: "accent" as const },
];

// ─── Connector Status Panel ──────────────────────────────────────────────────

function ConnectorStatusPanel({ investigations }: { investigations: Investigation[] }) {
  const recent = [...investigations].sort(
    (a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
  )[0];

  const connectorsRes = useConnectors(recent?.id);
  const connectors = connectorsRes.data ?? [];

  const success = connectors.filter((c) => c.status === "success").length;
  const failed = connectors.filter((c) => c.status === "failed").length;
  const running = connectors.filter((c) => c.status === "running").length;
  const queued = connectors.filter((c) => c.status === "queued").length;
  const total = connectors.length;

  const stats = [
    { label: "SUCCESS", count: success, icon: CheckCircle2, color: "text-success" },
    { label: "RUNNING", count: running, icon: Activity, color: "text-primary" },
    { label: "FAILED", count: failed, icon: XCircle, color: "text-destructive" },
    { label: "QUEUED", count: queued, icon: Clock3, color: "text-muted-foreground" },
  ];

  return (
    <Card className="p-4 border-border bg-surface rounded-md">
      <div className="flex items-center justify-between pb-3 mb-3 border-b border-border/60">
        <h3 className="font-display text-xs font-bold uppercase tracking-wider text-foreground">Connector Status</h3>
        {recent && (
          <span className="text-[10px] font-mono text-muted-foreground truncate max-w-[140px]">
            Target: {recent.name}
          </span>
        )}
      </div>

      {total === 0 ? (
        <EmptyState
          title="No connector runs yet"
          description="Run an investigation to see connector results here."
          className="py-4"
        />
      ) : (
        <>
          <div className="grid grid-cols-2 gap-2 mb-3">
            {stats.map((s) => {
              const Icon = s.icon;
              return (
                <div key={s.label} className="flex items-center gap-2 p-2 rounded-sm bg-surface-2 border border-border">
                  <Icon className={cn("h-3.5 w-3.5 shrink-0", s.color)} />
                  <div>
                    <div className="text-sm font-mono font-bold text-foreground">{s.count}</div>
                    <div className="text-[9px] font-mono text-muted-foreground">{s.label}</div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Mini connector list */}
          <div className="space-y-1 max-h-36 overflow-y-auto divide-y divide-border/30">
            {connectors.slice(0, 6).map((c) => (
              <div key={c.id} className="flex items-center gap-2 text-xs pt-1.5 first:pt-0">
                <StatusBadge status={c.status} />
                <span className="flex-1 truncate text-muted-foreground font-mono text-[11px]">{c.name}</span>
                <span className="font-mono text-[10px] text-muted-foreground/70">{c.runtime}</span>
              </div>
            ))}
          </div>
        </>
      )}
    </Card>
  );
}

// ─── Execution Summary Panel ─────────────────────────────────────────────────

function ExecutionSummaryPanel({ investigations }: { investigations: Investigation[] }) {
  const total = investigations.length;
  const completed = investigations.filter((i) => i.status === "completed").length;
  const active = investigations.filter((i) => i.status === "active").length;
  const failed = investigations.filter((i) => i.status === "failed").length;
  const successRate = total > 0 ? Math.round(((completed) / total) * 100) : 0;

  return (
    <Card className="p-4 border-border bg-surface rounded-md">
      <div className="flex items-center gap-2 pb-3 mb-3 border-b border-border/60">
        <Zap className="h-3.5 w-3.5 text-primary" />
        <h3 className="font-display text-xs font-bold uppercase tracking-wider text-foreground">Execution Summary</h3>
      </div>
      <div className="space-y-3">
        <div className="flex items-center justify-between text-xs font-mono">
          <span className="text-muted-foreground">Global Success Rate</span>
          <span className="font-bold text-success">{successRate}%</span>
        </div>
        <div className="h-1.5 rounded-sm bg-surface-3 overflow-hidden">
          <div
            className="h-full bg-success rounded-sm transition-all"
            style={{ width: `${successRate}%` }}
          />
        </div>
        <div className="grid grid-cols-3 gap-2 mt-3 font-mono">
          {[
            { label: "ACTIVE", value: active, color: "text-primary" },
            { label: "DONE", value: completed, color: "text-success" },
            { label: "FAILED", value: failed, color: "text-destructive" },
          ].map((s) => (
            <div key={s.label} className="text-center p-2 rounded-sm bg-surface-2 border border-border">
              <div className={cn("text-base font-bold", s.color)}>{s.value}</div>
              <div className="text-[9px] text-muted-foreground">{s.label}</div>
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
}

// ─── Activity Feed ───────────────────────────────────────────────────────────

function ActivityFeedPanel({ investigations }: { investigations: Investigation[] }) {
  const recent = [...investigations]
    .sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime())
    .slice(0, 6);

  return (
    <Card className="p-4 border-border bg-surface rounded-md">
      <div className="flex items-center justify-between pb-3 mb-3 border-b border-border/60">
        <div className="flex items-center gap-2">
          <TrendingUp className="h-3.5 w-3.5 text-accent" />
          <h3 className="font-display text-xs font-bold uppercase tracking-wider text-foreground">Recent Activity Log</h3>
        </div>
        <span className="text-[9px] font-mono uppercase tracking-widest text-success flex items-center gap-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-success" aria-hidden="true" /> LIVE
        </span>
      </div>
      {recent.length === 0 ? (
        <EmptyState title="No activity yet" description="Start an investigation to see activity." className="py-4" />
      ) : (
        <div className="space-y-1.5">
          {recent.map((inv) => (
            <Link
              key={inv.id}
              to="/investigations/$id"
              params={{ id: inv.id }}
              className="flex items-center gap-2.5 p-2 rounded-sm bg-surface-2/40 hover:bg-surface-3 transition border border-border/40 group"
            >
              <StatusBadge status={inv.status} />
              <div className="min-w-0 flex-1">
                <div className="text-xs font-medium truncate group-hover:text-primary transition-colors text-foreground">
                  {inv.name}
                </div>
                <div className="text-[10px] text-muted-foreground font-mono truncate">{inv.target || "—"}</div>
              </div>
              <time className="text-[10px] font-mono text-muted-foreground shrink-0">
                {fmtDate(inv.updatedAt)}
              </time>
            </Link>
          ))}
        </div>
      )}
    </Card>
  );
}

// ─── Dashboard page ──────────────────────────────────────────────────────────

function Dashboard() {
  const statsRes = useDashboardStats();
  const invRes = useInvestigations();
  const timelineRes = useTimeline();

  return (
    <AppShell
      title="Command Center"
      subtitle="Operational overview & active OSINT investigations"
      actions={
        <Link to="/investigations/new">
          <Button size="sm" className="bg-primary text-primary-foreground hover:bg-primary/90 gap-1.5 text-xs font-medium rounded-sm">
            <Plus className="h-3.5 w-3.5" aria-hidden="true" /> New Investigation
          </Button>
        </Link>
      }
    >
      {/* Stat cards grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3">
        <AsyncBoundary resource={statsRes}>
          {(stats) => (
            <>
              {stats.map((s) => (
                <StatCard key={s.label} stat={s} />
              ))}
            </>
          )}
        </AsyncBoundary>
      </div>

      {/* Main content grid */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-3 mt-4">
        {/* Recent investigations — 2/3 width */}
        <SectionCard
          title="Active Investigations"
          subtitle="Ongoing cases and recent target updates"
          className="xl:col-span-2"
          action={<ViewAllLink to="/investigations" />}
        >
          <AsyncBoundary
            resource={invRes}
            isEmpty={(list) => list.length === 0}
          >
            {(list) => (
              <div className="space-y-1.5">
                {list.slice(0, 5).map((inv) => (
                  <InvestigationRow key={inv.id} investigation={inv} />
                ))}
              </div>
            )}
          </AsyncBoundary>
        </SectionCard>

        {/* Right column */}
        <div className="space-y-3">
          {/* Quick Actions */}
          <Card className="p-4 border-border bg-surface rounded-md">
            <h3 className="font-display text-xs font-bold uppercase tracking-wider text-foreground">Quick Tools</h3>
            <p className="text-[11px] text-muted-foreground mt-0.5">Direct workflow entry points</p>
            <div className="mt-3 grid grid-cols-2 gap-2">
              {quickActions.map((a) => (
                <Link
                  key={a.label}
                  to={a.to}
                  className="flex items-center gap-2 p-2 rounded-sm bg-surface-2 border border-border hover:border-primary/50 hover:bg-surface-3 transition focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary"
                >
                  <div
                    className={cn(
                      "h-7 w-7 rounded-sm grid place-items-center shrink-0 border border-border",
                      a.tone === "primary" ? "bg-primary/10 text-primary" : "bg-accent/10 text-accent",
                    )}
                    aria-hidden="true"
                  >
                    <a.icon className="h-3.5 w-3.5" />
                  </div>
                  <span className="text-xs font-medium text-foreground truncate">{a.label}</span>
                </Link>
              ))}
            </div>
          </Card>

          {/* Live Feed */}
          <Card className="p-4 border-border bg-surface rounded-md">
            <div className="flex items-center justify-between pb-2 mb-2 border-b border-border/60">
              <h3 className="font-display text-xs font-bold uppercase tracking-wider text-foreground">Live Telemetry Feed</h3>
              <span className="text-[9px] font-mono uppercase tracking-widest text-success flex items-center gap-1.5">
                <span className="h-1.5 w-1.5 rounded-full bg-success" aria-hidden="true" /> LIVE
              </span>
            </div>
            <div className="mt-2 space-y-2.5">
              <AsyncBoundary resource={timelineRes} isEmpty={(l) => l.length === 0}>
                {(events) => (
                  <>
                    {events.slice(0, 4).map((e) => (
                      <TimelineFeedItem key={e.id} event={e} />
                    ))}
                  </>
                )}
              </AsyncBoundary>
            </div>
          </Card>
        </div>
      </div>

      {/* Bottom row: Connector status + Execution summary + Activity */}
      <AsyncBoundary resource={invRes}>
        {(investigations) => (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-4">
            <ConnectorStatusPanel investigations={investigations} />
            <ExecutionSummaryPanel investigations={investigations} />
            <ActivityFeedPanel investigations={investigations} />
          </div>
        )}
      </AsyncBoundary>
    </AppShell>
  );
}

