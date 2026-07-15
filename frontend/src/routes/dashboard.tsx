import { createFileRoute, Link } from "@tanstack/react-router";
import { AppShell } from "@/components/app-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Plus, Fingerprint, Network, FileText } from "lucide-react";
import { AsyncBoundary } from "@/components/states";
import { StatCard } from "@/components/dashboard/stat-card";
import { SectionCard, ViewAllLink } from "@/components/section-card";
import { InvestigationRow } from "@/components/investigations/investigation-row";
import { TimelineFeedItem } from "@/components/timeline/timeline-feed-item";
import {
  useDashboardStats,
  useInvestigations,
  useTimeline,
} from "@/hooks/use-osint-data";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/dashboard")({
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

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4 mt-6">
        {/* Recent investigations */}
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

        {/* Quick actions */}
        <div className="space-y-4">
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
    </AppShell>
  );
}
