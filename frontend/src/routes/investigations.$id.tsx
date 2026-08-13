import React, { useEffect, useRef } from "react";
import { createFileRoute, redirect, Link } from "@tanstack/react-router";
import { isAuthenticated } from "@/lib/auth";
import { AppShell } from "@/components/app-shell";

import { StatusBadge, SeverityBadge } from "@/components/badges";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  Mail, Globe, User, Wallet, Share2, Phone, Server,
  Network, Clock, FileText, ArrowLeft, Play, RefreshCw, AlertTriangle,
  CheckCircle2, XCircle, Loader2, RotateCcw, ExternalLink,
} from "lucide-react";
import { AsyncBoundary, EmptyState } from "@/components/states";
import { ConfidenceBar } from "@/components/confidence-bar";
import { ConnectorTimeline } from "@/components/investigations/connector-timeline";
import { fmtDate } from "@/lib/format";
import { cn } from "@/lib/utils";
import {
  useConnectors,
  useExecuteInvestigation,
  useIdentifiers,
  useInvestigation,
} from "@/hooks/use-osint-data";
import type { Connector, Identifier, IdentifierType } from "@/types/domain";

export const Route = createFileRoute("/investigations/$id")({
  beforeLoad: () => {
    if (!isAuthenticated()) throw redirect({ to: "/auth" });
  },
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
  mac: Server,
};


const jumpLinks = [
  { icon: Network, label: "Graph View", to: "/graph" as const },
  { icon: User, label: "Identity Profile", to: "/identity" as const },
  { icon: Clock, label: "Timeline", to: "/timeline" as const },
  { icon: FileText, label: "Reports", to: "/reports" as const },
];

// ─── Identifier table ─────────────────────────────────────────────────────────

function IdentifierTable({ items }: { items: Identifier[] }) {
  if (items.length === 0) {
    return <EmptyState title="No identifiers enriched yet." description="Run connectors to gather identifiers." />;
  }

  const hasProfileLinks = items.some((i) => i.profileUrl);

  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="text-left text-[11px] uppercase tracking-wider text-muted-foreground border-b border-border/60">
          <th scope="col" className="px-5 py-3 font-medium">Type</th>
          <th scope="col" className="px-5 py-3 font-medium">Value</th>
          <th scope="col" className="px-5 py-3 font-medium">Confidence</th>
          <th scope="col" className="px-5 py-3 font-medium">Sources</th>
          {hasProfileLinks && (
            <th scope="col" className="px-5 py-3 font-medium">Profile</th>
          )}
        </tr>
      </thead>
      <tbody>
        {items.map((i) => {
          const Icon = typeIcon[i.type] || Server;

          // Display platform / metadata label if available, otherwise default to identifier type name
          const displayType = i.platformDisplayName || i.type;


          // Build the value cell — actual domain hostnames become clickable links.
          let valueCell = (
            <span className="font-mono text-xs break-all">{i.value}</span>
          );
          const isDomainUrl =
            i.type === "domain" &&
            i.value.includes(".") &&
            !i.value.startsWith("Yes") &&
            !i.value.startsWith("No");

          if (isDomainUrl) {
            const href = i.value.startsWith("http") ? i.value : `https://${i.value}`;
            valueCell = (
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                id={`domain-link-${i.id}`}
                className="font-mono text-xs break-all text-accent hover:underline inline-flex items-center gap-1"
              >
                {i.value}
                <ExternalLink className="h-3 w-3 shrink-0" aria-hidden="true" />
              </a>
            );
          }

          return (
            <tr key={i.id} className="border-b border-border/40 hover:bg-white/[0.02]">
              <td className="px-5 py-3">
                <div className="flex items-center gap-2">
                  <div className="h-7 w-7 rounded-md bg-accent/10 text-accent grid place-items-center" aria-hidden="true">
                    <Icon className="h-3.5 w-3.5" />
                  </div>
                  <span className="text-xs capitalize text-muted-foreground">{displayType}</span>
                </div>
              </td>
              <td className="px-5 py-3">{valueCell}</td>
              <td className="px-5 py-3 w-56">
                <ConfidenceBar value={i.confidence} ariaLabel={`Confidence for ${i.value}`} />
              </td>
              <td className="px-5 py-3 text-xs">{i.sources}</td>
              {hasProfileLinks && (
                <td className="px-5 py-3">
                  {i.profileUrl ? (
                    <a
                      href={i.profileUrl.startsWith("http") ? i.profileUrl : `https://${i.profileUrl}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      id={`view-profile-${i.id}`}
                      className="inline-flex items-center gap-1.5 text-xs font-medium text-accent hover:text-accent/80 transition-colors px-2.5 py-1 rounded-md bg-accent/10 hover:bg-accent/20"
                    >
                      <ExternalLink className="h-3 w-3" aria-hidden="true" />
                      View Profile
                    </a>
                  ) : (
                    <span className="text-xs text-muted-foreground/40">—</span>
                  )}
                </td>
              )}
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

// ─── Connector card ───────────────────────────────────────────────────────────

function ConnectorCard({
  connector,
  onRetry,
  isRetrying,
}: {
  connector: Connector;
  onRetry?: () => void;
  isRetrying?: boolean;
}) {
  const c = connector;

  const statusConfig = {
    success: { icon: CheckCircle2, color: "text-success", bg: "bg-success/15", label: "Succeeded" },
    failed: { icon: XCircle, color: "text-destructive", bg: "bg-destructive/15", label: "Failed" },
    running: { icon: Loader2, color: "text-primary", bg: "bg-primary/15", label: "Running" },
    queued: { icon: Clock, color: "text-muted-foreground", bg: "bg-white/5", label: "Queued" },
  };

  const cfg = statusConfig[c.status as keyof typeof statusConfig] ?? statusConfig.queued;
  const Icon = cfg.icon;

  return (
    <Card
      className={cn(
        "glass p-4 border-border/60 flex flex-col gap-3",
        c.status === "failed" && "border-destructive/30"
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="text-[10px] uppercase tracking-widest text-muted-foreground">{c.category}</div>
          <div className="font-medium mt-0.5 truncate">{c.name}</div>
        </div>
        <div className={cn("h-7 w-7 rounded-md grid place-items-center shrink-0", cfg.bg)} aria-hidden="true">
          <Icon className={cn("h-3.5 w-3.5", cfg.color, c.status === "running" && "animate-spin")} />
        </div>
      </div>

      {/* Stats row */}
      <div className="flex items-center gap-4 text-xs text-muted-foreground">
        <span>
          Hits: <span className="text-foreground font-mono font-medium">{c.hits}</span>
        </span>
        <span>
          Runtime: <span className="text-foreground font-mono">{c.runtime}</span>
        </span>
        <span className={cn("ml-auto text-[10px] font-medium px-2 py-0.5 rounded-full", cfg.bg, cfg.color)}>
          {cfg.label}
        </span>
      </div>

      {/* Running progress bar */}
      {c.status === "running" && (
        <div
          className="h-1 bg-white/5 rounded-full overflow-hidden"
          role="progressbar"
          aria-label={`${c.name} running`}
        >
          <div className="h-full w-1/2 bg-gradient-to-r from-primary to-accent animate-pulse" />
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-2">
        <Button
          size="sm"
          variant="ghost"
          className="h-7 gap-1 text-xs"
          onClick={onRetry}
          disabled={isRetrying}
          aria-label={`Retry ${c.name}`}
        >
          {isRetrying ? (
            <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" />
          ) : (
            <RotateCcw className="h-3 w-3" aria-hidden="true" />
          )}
          {isRetrying ? "Running…" : "Re-run all"}
        </Button>
      </div>
    </Card>
  );
}

// ─── Skeleton loader for connector cards ─────────────────────────────────────

function ConnectorCardSkeleton() {
  return (
    <Card className="glass p-4 border-border/60 animate-pulse">
      <div className="flex items-start justify-between">
        <div className="space-y-2">
          <div className="h-2.5 w-20 rounded bg-white/10" />
          <div className="h-4 w-32 rounded bg-white/10" />
        </div>
        <div className="h-7 w-7 rounded-md bg-white/10" />
      </div>
      <div className="mt-4 flex gap-3">
        <div className="h-3 w-16 rounded bg-white/10" />
        <div className="h-3 w-20 rounded bg-white/10" />
      </div>
    </Card>
  );
}

// ─── Detail page ──────────────────────────────────────────────────────────────

function Detail() {
  const { id } = Route.useParams();
  const invRes = useInvestigation(id);
  const identifiersRes = useIdentifiers(id);
  const connectorsRes = useConnectors(id);
  const execute = useExecuteInvestigation();

  const deriveIdentifierType = (target: string): IdentifierType => {
    if (!target) return "domain";
    const cleaned = target.trim();
    if (cleaned.includes("@")) return "email";
    if (
      cleaned.startsWith("0x") ||
      cleaned.length === 42 ||
      /^1[1-9A-HJ-NP-Za-km-z]{25,34}$/.test(cleaned) ||
      /^3[1-9A-HJ-NP-Za-km-z]{25,34}$/.test(cleaned) ||
      /^bc1[a-zA-Z0-9]{25,87}$/i.test(cleaned) ||
      /^[1-9A-HJ-NP-Za-km-z]{32,44}$/.test(cleaned)
    ) {
      return "wallet";
    }
    if (cleaned.match(/^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/)) return "ip";
    // MAC address check MUST happen before IPv6 since MACs also use colons and hex digits
    if (/^(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}$|^(?:[0-9A-Fa-f]{4}\.){2}[0-9A-Fa-f]{4}$|^[0-9A-Fa-f]{12}$/.test(cleaned)) return "mac";
    // IPv6 check
    if (cleaned.includes(":") && /^[0-9a-fA-F:]+$/.test(cleaned)) return "ip";
    if (cleaned.match(/^\+?\d+$/)) return "phone";
    if (cleaned.startsWith("@")) return "username";
    return "domain";
  };



  const handleExecute = async (inv: { id: string; target: string; seedType?: IdentifierType }) => {
    if (!inv.target) return;
    const identifierType = inv.seedType ?? deriveIdentifierType(inv.target);
    try {
      await execute.mutate({
        investigationId: inv.id,
        identifier: { value: inv.target, type: identifierType },
      });
      invRes.refetch?.();
      identifiersRes.refetch?.();
      connectorsRes.refetch?.();
      setTimeout(() => {
        invRes.refetch?.();
        identifiersRes.refetch?.();
        connectorsRes.refetch?.();
      }, 500);
    } catch {
      // Error in execute.error
    }
  };


  // Derive progress from connector results
  const connectors = connectorsRes.data ?? [];
  const totalConnectors = connectors.length;
  const doneConnectors = connectors.filter(
    (c) => c.status === "success" || c.status === "failed"
  ).length;
  const derivedProgress =
    execute.data?.statistics
      ? Math.round(
          (execute.data.statistics.successfulConnectors /
            Math.max(execute.data.statistics.executedConnectors, 1)) *
            100
        )
      : totalConnectors > 0
      ? Math.round((doneConnectors / totalConnectors) * 100)
      : invRes.data?.progress ?? 0;

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
                <span className="font-mono">{inv.target || "—"}</span>
              </>
            }
            actions={
              <div className="flex items-center gap-2">
                <Link to="/investigations">
                  <Button variant="ghost" className="gap-2">
                    <ArrowLeft className="h-4 w-4" aria-hidden="true" /> All cases
                  </Button>
                </Link>
                <Button
                  variant="secondary"
                  className="gap-2"
                  onClick={() => {
                    invRes.refetch?.();
                    identifiersRes.refetch?.();
                    connectorsRes.refetch?.();
                  }}
                >
                  <RefreshCw className="h-4 w-4" aria-hidden="true" /> Refresh
                </Button>
                <Button
                  onClick={() => handleExecute(inv)}
                  disabled={execute.isPending || !inv.target}
                  className="gap-2 bg-gradient-to-r from-primary to-accent text-primary-foreground"
                >
                  <Play className="h-4 w-4" aria-hidden="true" />
                  {execute.isPending ? "Executing…" : "Run all connectors"}
                </Button>
              </div>
            }
          >
            {/* Execution error banner */}
            {execute.error && (
              <Card className="glass border-destructive/40 p-4 mb-4" role="alert">
                <div className="flex items-center gap-3">
                  <AlertTriangle className="h-4 w-4 text-destructive shrink-0" aria-hidden="true" />
                  <div>
                    <div className="text-sm font-medium text-destructive">Execution failed</div>
                    <div className="text-xs text-muted-foreground mt-0.5">{execute.error.message}</div>
                  </div>
                  <Button variant="ghost" size="sm" className="ml-auto text-xs" onClick={() => execute.reset()}>
                    Dismiss
                  </Button>
                </div>
              </Card>
            )}

            {/* Execution success banner */}
            {execute.data && !execute.isPending && !execute.error && (
              <Card className="glass border-primary/40 p-4 mb-4">
                <div className="flex items-center gap-3">
                  <div className="h-7 w-7 rounded-md bg-primary/10 text-primary grid place-items-center">
                    <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
                  </div>
                  <div className="flex-1">
                    <div className="text-sm font-medium">
                      Execution {execute.data.status === "completed" ? "completed" : execute.data.status}
                    </div>
                    {execute.data.statistics && (
                      <div className="text-xs text-muted-foreground mt-0.5 flex gap-3 flex-wrap">
                        <span>{execute.data.statistics.executedConnectors} connectors</span>
                        <span className="text-success">{execute.data.statistics.successfulConnectors} succeeded</span>
                        {execute.data.statistics.failedConnectors > 0 && (
                          <span className="text-destructive">{execute.data.statistics.failedConnectors} failed</span>
                        )}
                        <span>{execute.data.statistics.normalizedFactsCount} facts</span>
                        {execute.data.statistics.executionDurationSeconds != null && (
                          <span>{execute.data.statistics.executionDurationSeconds.toFixed(1)}s</span>
                        )}
                      </div>
                    )}
                  </div>
                  <Button variant="ghost" size="sm" className="text-xs" onClick={() => execute.reset()}>
                    Dismiss
                  </Button>
                </div>
              </Card>
            )}

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
                    { label: "Progress", value: `${derivedProgress}%` },
                    { label: "Identifiers", value: identifiersRes.data?.length ?? inv.identifiers },
                    { label: "Connectors", value: connectorsRes.data?.length ?? inv.connectors },
                    { label: "Created", value: fmtDate(inv.createdAt) },
                  ].map((m) => (
                    <div key={m.label}>
                      <div className="text-[10px] uppercase tracking-widest text-muted-foreground">{m.label}</div>
                      <div className="text-lg font-display font-semibold mt-0.5">{m.value}</div>
                    </div>
                  ))}
                </div>
                <Progress value={derivedProgress} className="h-1.5 mt-4" />
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
                <TabsTrigger value="execution">Execution Log</TabsTrigger>
                <TabsTrigger value="activity">Activity</TabsTrigger>
              </TabsList>

              {/* Identifiers tab */}
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

              {/* Connectors tab */}
              <TabsContent value="connectors">
                {connectorsRes.isLoading ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                    {Array.from({ length: 6 }).map((_, i) => (
                      <ConnectorCardSkeleton key={i} />
                    ))}
                  </div>
                ) : (
                  <AsyncBoundary
                    resource={connectorsRes}
                    isEmpty={(items) => items.length === 0}
                  >
                    {(items) => (
                      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                        {items.map((c) => (
                          <ConnectorCard
                            key={c.id}
                            connector={c}
                            onRetry={() => handleExecute(inv)}
                            isRetrying={execute.isPending}
                          />
                        ))}
                      </div>
                    )}
                  </AsyncBoundary>
                )}
              </TabsContent>

              {/* Execution log tab */}
              <TabsContent value="execution">
                <Card className="glass p-6 border-border/60">
                  <h3 className="font-display font-semibold mb-4">Execution Timeline</h3>
                  {execute.data?.connectorResults && execute.data.connectorResults.length > 0 ? (
                    <ConnectorTimeline results={execute.data.connectorResults} />
                  ) : (
                    <EmptyState
                      title="No execution log yet"
                      description="Run all connectors to see a step-by-step execution timeline."
                      action={
                        <Button
                          onClick={() => handleExecute(inv)}
                          disabled={execute.isPending || !inv.target}
                          className="gap-2 bg-gradient-to-r from-primary to-accent text-primary-foreground"
                        >
                          <Play className="h-3.5 w-3.5" aria-hidden="true" /> Run now
                        </Button>
                      }
                    />
                  )}
                </Card>
              </TabsContent>

              {/* Activity tab */}
              <TabsContent value="activity">
                <Card className="glass p-6 border-border/60 text-sm text-muted-foreground">
                  See the full chronological event log in the{" "}
                  <Link to="/timeline" className="text-primary hover:underline">Timeline</Link> view,
                  or switch to the <span className="text-foreground">Execution Log</span> tab above for
                  per-connector timing details.
                </Card>
              </TabsContent>
            </Tabs>
          </AppShell>
        );
      }}
    </AsyncBoundary>
  );
}
