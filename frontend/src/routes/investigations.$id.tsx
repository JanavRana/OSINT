import { createFileRoute, Link } from "@tanstack/react-router";
import { AppShell } from "@/components/app-shell";
import { StatusBadge, SeverityBadge } from "@/components/badges";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  Mail, Globe, User, Wallet, Share2, Phone, Server,
  Network, Clock, FileText, ArrowLeft, Play, Pause, RefreshCw,
} from "lucide-react";
import { AsyncBoundary, EmptyState } from "@/components/states";
import { ConfidenceBar } from "@/components/confidence-bar";
import { fmtDate } from "@/lib/format";
import { useConnectors, useExecuteInvestigation, useIdentifiers, useInvestigation } from "@/hooks/use-osint-data";
import type { Connector, Identifier, IdentifierType } from "@/types/domain";

export const Route = createFileRoute("/investigations/$id")({
  head: ({ params }) => ({ meta: [{ title: `${params.id} — AXIOM OSINT` }] }),
  component: Detail,
});

const typeIcon: Record<IdentifierType, typeof Mail> = {
  email: Mail,
  domain: Globe,
  username: User,
  wallet: Wallet,
  social: Share2,
  phone: Phone,
  ip: Server,
};

const jumpLinks = [
  { icon: Network, label: "Graph View", to: "/graph" as const },
  { icon: User, label: "Identity Profile", to: "/identity" as const },
  { icon: Clock, label: "Timeline", to: "/timeline" as const },
  { icon: FileText, label: "Reports", to: "/reports" as const },
];

function IdentifierTable({ items }: { items: Identifier[] }) {
  if (items.length === 0) {
    return <EmptyState title="No identifiers enriched yet." description="Run a connector to gather identifiers." />;
  }
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="text-left text-[11px] uppercase tracking-wider text-muted-foreground border-b border-border/60">
          <th scope="col" className="px-5 py-3 font-medium">Type</th>
          <th scope="col" className="px-5 py-3 font-medium">Value</th>
          <th scope="col" className="px-5 py-3 font-medium">Confidence</th>
          <th scope="col" className="px-5 py-3 font-medium">Sources</th>
          <th scope="col" className="px-5 py-3 font-medium">First seen</th>
        </tr>
      </thead>
      <tbody>
        {items.map((i) => {
          const Icon = typeIcon[i.type];
          return (
            <tr key={i.id} className="border-b border-border/40 hover:bg-white/[0.02]">
              <td className="px-5 py-3">
                <div className="flex items-center gap-2">
                  <div className="h-7 w-7 rounded-md bg-accent/10 text-accent grid place-items-center" aria-hidden="true">
                    <Icon className="h-3.5 w-3.5" />
                  </div>
                  <span className="text-xs capitalize text-muted-foreground">{i.type}</span>
                </div>
              </td>
              <td className="px-5 py-3 font-mono text-xs break-all">{i.value}</td>
              <td className="px-5 py-3 w-56">
                <ConfidenceBar value={i.confidence} ariaLabel={`Confidence for ${i.value}`} />
              </td>
              <td className="px-5 py-3 text-xs">{i.sources}</td>
              <td className="px-5 py-3 text-xs text-muted-foreground">{i.firstSeen}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

function ConnectorCard({ connector }: { connector: Connector }) {
  const c = connector;
  return (
    <Card className="glass p-4 border-border/60">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-[10px] uppercase tracking-widest text-muted-foreground">{c.category}</div>
          <div className="font-medium mt-0.5">{c.name}</div>
        </div>
        <StatusBadge status={c.status} />
      </div>
      <div className="mt-3 flex items-center justify-between text-xs text-muted-foreground">
        <span>Hits: <span className="text-foreground font-mono">{c.hits}</span></span>
        <span>Runtime: <span className="text-foreground font-mono">{c.runtime}</span></span>
      </div>
      {c.status === "running" && (
        <div
          className="mt-3 h-1 bg-white/5 rounded-full overflow-hidden"
          role="progressbar"
          aria-label={`${c.name} running`}
        >
          <div className="h-full w-1/2 bg-gradient-to-r from-primary to-accent animate-pulse" />
        </div>
      )}
      <div className="mt-3 flex gap-2">
        <Button size="sm" variant="ghost" className="h-7 gap-1">
          <Play className="h-3 w-3" aria-hidden="true" /> Rerun
        </Button>
        <Button size="sm" variant="ghost" className="h-7 gap-1">
          <Pause className="h-3 w-3" aria-hidden="true" /> Pause
        </Button>
      </div>
    </Card>
  );
}

function Detail() {
  const { id } = Route.useParams();
  const invRes = useInvestigation(id);
  const identifiersRes = useIdentifiers(id);
  const connectorsRes = useConnectors(id);
  const execute = useExecuteInvestigation();

  return (
    <AsyncBoundary
      resource={invRes}
      isEmpty={(inv) => inv === undefined}
      empty={
        <AppShell title="Investigation not found">
          <EmptyState
            title="This case could not be found"
            description={`No investigation matches the id ${id}.`}
            action={
              <Link to="/investigations">
                <Button variant="secondary" className="gap-2">
                  <ArrowLeft className="h-4 w-4" aria-hidden="true" /> Back to all cases
                </Button>
              </Link>
            }
          />
        </AppShell>
      }
    >
      {(maybeInv) => {
        const inv = maybeInv!;
        return (
          <AppShell
            title={inv.name}
            subtitle={
              <>
                <span className="font-mono text-xs">{inv.id}</span> · target{" "}
                <span className="font-mono">{inv.target}</span>
              </>
            }
            actions={
              <div className="flex items-center gap-2">
                <Link to="/investigations">
                  <Button variant="ghost" className="gap-2">
                    <ArrowLeft className="h-4 w-4" aria-hidden="true" /> All cases
                  </Button>
                </Link>
                <Button variant="secondary" className="gap-2" onClick={() => invRes.refetch?.()}>
                  <RefreshCw className="h-4 w-4" aria-hidden="true" /> Refresh
                </Button>
                <Button
                  onClick={() => execute.mutate(inv.id).catch(() => {})}
                  disabled={execute.isPending}
                  className="gap-2 bg-gradient-to-r from-primary to-accent text-primary-foreground"
                >
                  <Play className="h-4 w-4" aria-hidden="true" />
                  {execute.isPending ? "Queuing…" : "Run all connectors"}
                </Button>
              </div>
            }
          >
            {/* Overview */}
            <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
              <Card className="glass p-5 border-border/60 lg:col-span-3">
                <div className="flex flex-wrap items-center gap-3">
                  <StatusBadge status={inv.status} />
                  <SeverityBadge severity={inv.severity} />
                  {inv.tags.map((t) => (
                    <span
                      key={t}
                      className="text-[10px] uppercase tracking-widest px-2 py-0.5 rounded-md bg-white/5 text-muted-foreground border border-border/60"
                    >
                      #{t}
                    </span>
                  ))}
                  <div className="ml-auto text-xs text-muted-foreground">
                    Owner <span className="text-foreground">{inv.owner}</span> · Updated {fmtDate(inv.updatedAt)}
                  </div>
                </div>
                <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4">
                  {[
                    { label: "Progress", value: `${inv.progress}%` },
                    { label: "Identifiers", value: inv.identifiers },
                    { label: "Connectors", value: inv.connectors },
                    { label: "Created", value: fmtDate(inv.createdAt) },
                  ].map((m) => (
                    <div key={m.label}>
                      <div className="text-[10px] uppercase tracking-widest text-muted-foreground">{m.label}</div>
                      <div className="text-lg font-display font-semibold mt-0.5">{m.value}</div>
                    </div>
                  ))}
                </div>
                <Progress value={inv.progress} className="h-1.5 mt-4" />
              </Card>

              <Card className="glass p-5 border-border/60">
                <h3 className="font-display font-semibold">Jump to</h3>
                <div className="mt-3 space-y-2">
                  {jumpLinks.map((l) => (
                    <Link
                      key={l.label}
                      to={l.to}
                      className="flex items-center gap-3 p-2 rounded-lg hover:bg-white/5 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
                    >
                      <l.icon className="h-4 w-4 text-primary" aria-hidden="true" />
                      {l.label}
                    </Link>
                  ))}
                </div>
              </Card>
            </div>

            {/* Tabs */}
            <Tabs defaultValue="identifiers" className="mt-6">
              <TabsList className="bg-surface/60 border border-border/60">
                <TabsTrigger value="identifiers">
                  Identifiers ({identifiersRes.data?.length ?? 0})
                </TabsTrigger>
                <TabsTrigger value="connectors">
                  Connectors ({connectorsRes.data?.length ?? 0})
                </TabsTrigger>
                <TabsTrigger value="activity">Activity</TabsTrigger>
              </TabsList>

              <TabsContent value="identifiers">
                <Card className="glass border-border/60 overflow-hidden">
                  <AsyncBoundary
                    resource={identifiersRes}
                    isEmpty={(items) => items.length === 0}
                  >
                    {(items) => <IdentifierTable items={items} />}
                  </AsyncBoundary>
                </Card>
              </TabsContent>

              <TabsContent value="connectors">
                <AsyncBoundary
                  resource={connectorsRes}
                  isEmpty={(items) => items.length === 0}
                >
                  {(items) => (
                    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                      {items.map((c) => <ConnectorCard key={c.id} connector={c} />)}
                    </div>
                  )}
                </AsyncBoundary>
              </TabsContent>

              <TabsContent value="activity">
                <Card className="glass p-6 border-border/60 text-sm text-muted-foreground">
                  See the full chronological event log in the{" "}
                  <Link to="/timeline" className="text-primary hover:underline">Timeline</Link> view.
                </Card>
              </TabsContent>
            </Tabs>
          </AppShell>
        );
      }}
    </AsyncBoundary>
  );
}
