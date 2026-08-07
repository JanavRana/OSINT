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
      { title: "Dashboard — AXIOM OSINT" },
      { name: "description", content: "Overview of active investigations, connector health, and recent intelligence events." },
    ],
  }),
  component: Dashboard,
});

const quickActions = [
  { icon: Plus, label: "New case", to: "/investigations/new" as const, tone: "primary" as const },
  { icon: Fingerprint, label: "Identity", to: "/identity" as const, tone: "accent" as const },
  { icon: Network, label: "Graph", to: "/graph" as const, tone: "primary" as const },
  { icon: FileText, label: "Reports", to: "/reports" as const, tone: "accent" as const },
];

// ─── Connector Status Panel ──────────────────────────────────────────────────

function ConnectorStatusPanel({ investigations }: { investigations: Investigation[] }) {
  // Use the most recently updated investigation to get connector status
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
    { label: "Success", count: success, icon: CheckCircle2, color: "text-success" },
    { label: "Running", count: running, icon: Activity, color: "text-primary" },
    { label: "Failed", count: failed, icon: XCircle, color: "text-destructive" },
    { label: "Queued", count: queued, icon: Clock3, color: "text-muted-foreground" },
  ];

  return (
    <Card className="glass p-5 border-border/60">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-display font-semibold">Connector Status</h3>
        {recent && (
          <span className="text-[10px] text-muted-foreground font-mono truncate max-w-[120px]">
            {recent.name}
          </span>
        )}
      </div>

      {total === 0 ? (
        <EmptyState
          title="No connector runs yet"
          description="Run an investigation to see connector results here."
          className="py-6"
        />
      ) : (
        <>
          <div className="grid grid-cols-2 gap-2 mb-4">
            {stats.map((s) => {
              const Icon = s.icon;
              return (
                <div key={s.label} className="flex items-center gap-2 p-2 rounded-lg bg-white/[0.03] border border-border/40">
                  <Icon className={cn("h-3.5 w-3.5 shrink-0", s.color)} />
                  <div>
                    <div className="text-base font-display font-bold">{s.count}</div>
                    <div className="text-[10px] text-muted-foreground">{s.label}</div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Mini connector list */}
          <div className="space-y-1 max-h-40 overflow-y-auto">
            {connectors.slice(0, 6).map((c) => (
              <div key={c.id} className="flex items-center gap-2 text-xs py-1">
                <StatusBadge status={c.status} />
                <span className="flex-1 truncate text-muted-foreground">{c.name}</span>
                <span className="font-mono text-[10px] text-muted-foreground">{c.runtime}</span>
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
  // Derive execution summary from investigation list
  const total = investigations.length;
  const completed = investigations.filter((i) => i.status === "completed").length;
  const active = investigations.filter((i) => i.status === "active").length;
  const failed = investigations.filter((i) => i.status === "failed").length;
  const successRate = total > 0 ? Math.round(((completed) / total) * 100) : 0;

  return (
    <Card className="glass p-5 border-border/60">
      <div className="flex items-center gap-2 mb-4">
        <Zap className="h-4 w-4 text-primary" />
        <h3 className="font-display font-semibold">Execution Summary</h3>
      </div>
      <div className="space-y-3">
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">Success rate</span>
          <span className="font-display font-bold text-success">{successRate}%</span>
        </div>
        <div className="h-2 rounded-full bg-white/5 overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-success to-primary rounded-full transition-all"
            style={{ width: `${successRate}%` }}
          />
        </div>
        <div className="grid grid-cols-3 gap-2 mt-3">
          {[
            { label: "Active", value: active, color: "text-primary" },
            { label: "Done", value: completed, color: "text-success" },
            { label: "Failed", value: failed, color: "text-destructive" },
          ].map((s) => (
            <div key={s.label} className="text-center p-2 rounded-lg bg-white/[0.03]">
              <div className={cn("text-lg font-display font-bold", s.color)}>{s.value}</div>
              <div className="text-[10px] text-muted-foreground">{s.label}</div>
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
}

// ─── Activity Feed ───────────────────────────────────────────────────────────

function ActivityFeedPanel({ investigations }: { investigations: Investigation[] }) {
  // Build a lightweight activity feed from investigation status changes (sorted by updatedAt)
  const recent = [...investigations]
    .sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime())
    .slice(0, 6);

  return (
    <Card className="glass p-5 border-border/60">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <TrendingUp className="h-4 w-4 text-accent" />
          <h3 className="font-display font-semibold">Recent Activity</h3>
        </div>
        <span className="text-[10px] uppercase tracking-widest text-success flex items-center gap-1">
          <span className="h-1.5 w-1.5 rounded-full bg-success pulse-ring" aria-hidden="true" /> Live
        </span>
      </div>
      {recent.length === 0 ? (
        <EmptyState title="No activity yet" description="Start an investigation to see activity." className="py-6" />
      ) : (
        <div className="space-y-2">
          {recent.map((inv) => (
            <Link
              key={inv.id}
              to="/investigations/$id"
              params={{ id: inv.id }}
              className="flex items-center gap-3 p-2 rounded-lg hover:bg-white/5 transition-colors group"
            >
              <StatusBadge status={inv.status} />
              <div className="min-w-0 flex-1">
                <div className="text-xs font-medium truncate group-hover:text-primary transition-colors">
                  {inv.name}
                </div>
                <div className="text-[10px] text-muted-foreground font-mono truncate">{inv.target || "—"}</div>
              </div>
              <time className="text-[10px] text-muted-foreground shrink-0">
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
      subtitle="Real-time overview of your OSINT operations"
      actions={
        <Link to="/investigations/new">
          <Button className="bg-gradient-to-r from-primary to-accent text-primary-foreground hover:opacity-90 gap-2">
            <Plus className="h-4 w-4" aria-hidden="true" /> New Investigation
          </Button>
        </Link>
      }
    >
      {/* Stat cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
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
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4 mt-6">
        {/* Recent investigations — 2/3 width */}
        <SectionCard
          title="Recent Investigations"
          subtitle="Ongoing and recently updated cases"
          className="xl:col-span-2"
          action={<ViewAllLink to="/investigations" />}
        >
          <AsyncBoundary
            resource={invRes}
            isEmpty={(list) => list.length === 0}
          >
            {(list) => (
              <div className="space-y-2">
                {list.slice(0, 5).map((inv) => (
                  <InvestigationRow key={inv.id} investigation={inv} />
                ))}
              </div>
            )}
          </AsyncBoundary>
        </SectionCard>

        {/* Right column */}
        <div className="space-y-4">
          {/* Quick Actions */}
          <Card className="glass p-5 border-border/60">
            <h3 className="font-display text-lg font-semibold">Quick Actions</h3>
            <p className="text-xs text-muted-foreground">Jump into common workflows</p>
            <div className="mt-4 grid grid-cols-2 gap-2">
              {quickActions.map((a) => (
                <Link
                  key={a.label}
                  to={a.to}
                  className="group flex flex-col items-start gap-2 p-3 rounded-xl bg-surface/60 border border-border/60 hover:border-primary/40 hover:bg-surface transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
                >
                  <div
                    className={cn(
                      "h-8 w-8 rounded-lg grid place-items-center",
                      a.tone === "primary" ? "bg-primary/15 text-primary" : "bg-accent/15 text-accent",
                    )}
                    aria-hidden="true"
                  >
                    <a.icon className="h-4 w-4" />
                  </div>
                  <span className="text-xs font-medium">{a.label}</span>
                </Link>
              ))}
            </div>
          </Card>

          {/* Live Feed (timeline events for the selected investigation context) */}
          <Card className="glass p-5 border-border/60">
            <div className="flex items-center justify-between">
              <h3 className="font-display text-lg font-semibold">Live Feed</h3>
              <span className="text-[10px] uppercase tracking-widest text-success flex items-center gap-1">
                <span className="h-1.5 w-1.5 rounded-full bg-success pulse-ring" aria-hidden="true" /> Live
              </span>
            </div>
            <div className="mt-3 space-y-3">
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
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
            <ConnectorStatusPanel investigations={investigations} />
            <ExecutionSummaryPanel investigations={investigations} />
            <ActivityFeedPanel investigations={investigations} />
          </div>
        )}
      </AsyncBoundary>
    </AppShell>
  );
}
