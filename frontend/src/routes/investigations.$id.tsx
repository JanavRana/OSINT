import React, { useState } from "react";
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
  CheckCircle2, XCircle, Loader2, RotateCcw, LayoutGrid, List, ExternalLink,
} from "lucide-react";
import { PLATFORM_BRANDS, getBrand, parseUrl, WebsiteIdentifierBadge } from "@/components/ui/website-profile-card";
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
  head: ({ params }) => ({ meta: [{ title: `${params.id} — IntelWeave` }] }),
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

// ─── Identifier dossier card ──────────────────────────────────────────────────

const typeStyle: Record<IdentifierType, { icon: typeof Mail; classes: string }> = {
  email:    { icon: Mail,   classes: "text-primary bg-primary/10 border-primary/40" },
  domain:   { icon: Globe,  classes: "text-accent bg-accent/10 border-accent/40" },
  username: { icon: User,   classes: "text-warning bg-warning/10 border-warning/40" },
  social:   { icon: User,   classes: "text-warning bg-warning/10 border-warning/40" },
  wallet:   { icon: Wallet, classes: "text-success bg-success/10 border-success/40" },
  phone:    { icon: Phone,  classes: "text-primary bg-primary/10 border-primary/40" },
  ip:       { icon: Server, classes: "text-destructive bg-destructive/10 border-destructive/40" },
  mac:      { icon: Server, classes: "text-destructive bg-destructive/10 border-destructive/40" },
};

function PlatformFaviconImage({ domain, fallbackIcon: FallbackIcon }: { domain: string; fallbackIcon: typeof Mail }) {
  const [errored, setErrored] = useState(false);
  const isKnown = domain ? Boolean(getBrand(domain) || PLATFORM_BRANDS[domain]) : false;

  if (!isKnown || errored) return <FallbackIcon className="h-4 w-4 text-muted-foreground" />;

  return (
    <img
      src={`https://www.google.com/s2/favicons?domain=${domain}&sz=64`}
      alt=""
      aria-hidden="true"
      className="h-full w-full object-contain"
      onError={() => setErrored(true)}
    />
  );
}

function IdentifierDossierCard({ item }: { item: Identifier }) {
  const style = typeStyle[item.type] ?? typeStyle.domain;
  const Icon = style.icon;
  const displayType = item.platformDisplayName || item.type;

  // Determine favicon domain: from profileUrl, value, or platform hint
  const profileParsed = item.profileUrl ? parseUrl(item.profileUrl) : null;
  let faviconDomain = profileParsed
    ? profileParsed.domain
    : item.platform ?? null;

  if (!faviconDomain) {
    if (item.type === "domain" && item.value.includes(".")) {
      faviconDomain = parseUrl(item.value).domain;
    } else if (item.value.includes("@")) {
      const parts = item.value.split("@");
      if (parts.length > 1 && parts[1].includes(".")) faviconDomain = parts[1];
    } else if (item.value.includes("t.me/")) {
      faviconDomain = "telegram.org";
    }
  }

  const brand = faviconDomain ? getBrand(faviconDomain) : null;
  const accentColor = brand?.accent;

  const isDomainUrl =
    item.type === "domain" &&
    item.value.includes(".") &&
    !item.value.startsWith("Yes") &&
    !item.value.startsWith("No");

  const externalHref = profileParsed
    ? profileParsed.href
    : isDomainUrl
    ? parseUrl(item.value).href
    : null;

  return (
    <div
      className={cn(
        "relative rounded-md border bg-surface-2/80 backdrop-blur-sm p-3 flex flex-col justify-between gap-2.5 min-h-[105px]",
        "hover:border-primary/50 transition-all duration-200"
      )}
      style={
        accentColor
          ? {
              borderColor: `${accentColor}40`,
              background: `linear-gradient(135deg, ${accentColor}12 0%, rgba(20, 24, 33, 0.85) 100%)`,
              boxShadow: `inset 0 0 25px -8px ${accentColor}20`,
            }
          : undefined
      }
    >
      {/* Top section: Avatar + Type & Value */}
      <div className="flex items-start gap-2.5 pr-9">
        {/* Platform logo avatar circle */}
        <div
          className="h-9 w-9 rounded-full border grid place-items-center shrink-0 bg-surface-3 overflow-hidden p-1.5"
          style={{
            borderColor: accentColor ? `${accentColor}60` : undefined,
            boxShadow: accentColor ? `0 0 8px ${accentColor}30` : undefined,
          }}
          aria-hidden="true"
        >
          {faviconDomain ? (
            <PlatformFaviconImage domain={faviconDomain} fallbackIcon={Icon} />
          ) : (
            <Icon className="h-4 w-4 text-muted-foreground" />
          )}
        </div>

        <div className="min-w-0 flex-1 flex flex-col justify-center">
          <div className="mb-1.5">
            <span
              className="inline-block text-[9px] font-mono font-bold uppercase tracking-widest px-1.5 py-0.5 rounded-sm border"
              style={
                accentColor
                  ? { color: accentColor, borderColor: `${accentColor}40`, background: `${accentColor}15` }
                  : undefined
              }
              aria-label={`Type: ${displayType}`}
            >
              {displayType}
            </span>
          </div>
          <div className="font-mono text-xs font-bold text-foreground truncate" title={item.value}>
            {item.value}
          </div>
        </div>
      </div>

      {/* Top right external profile link button — larger and prominent */}
      {externalHref && (
        <a
          href={externalHref}
          target="_blank"
          rel="noopener noreferrer"
          id={`dossier-link-${item.id}`}
          aria-label={`Open profile for ${item.value}`}
          className="absolute top-2.5 right-2.5 p-2 rounded-sm border border-border/70 bg-surface-2 text-muted-foreground hover:text-primary hover:border-primary/50 transition-colors shadow-sm"
          style={accentColor ? { color: accentColor, borderColor: `${accentColor}50` } : undefined}
        >
          <ExternalLink className="h-4 w-4" aria-hidden="true" />
        </a>
      )}

      {/* Bottom section: Confidence bar rating (tighter top padding) */}
      <div className="pt-1 border-t border-border/30">
        <ConfidenceBar value={item.confidence} ariaLabel={`Confidence for ${item.value}`} />
      </div>
    </div>
  );
}

// ─── Identifier table ─────────────────────────────────────────────────────────

type IdentifierView = "table" | "dossier";

function IdentifierTable({ items }: { items: Identifier[] }) {
  const [view, setView] = useState<IdentifierView>("dossier");

  if (items.length === 0) {
    return <EmptyState title="No identifiers enriched yet." description="Run connectors to gather identifiers." className="py-8" />;
  }

  const hasProfileLinks = items.some((i) => i.profileUrl);

  return (
    <div>
      {/* View toggle */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-border/60 bg-surface-2/40">
        <span className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground">
          {items.length} identifiers
        </span>
        <div
          className="flex items-center gap-0.5 rounded-sm border border-border bg-surface-2 p-0.5"
          role="group"
          aria-label="Switch identifier view"
        >
          <button
            id="view-toggle-table"
            onClick={() => setView("table")}
            aria-pressed={view === "table"}
            className={cn(
              "inline-flex items-center gap-1 px-2 py-1 rounded-sm text-[10px] font-mono transition-colors",
              view === "table" ? "bg-surface-3 text-foreground" : "text-muted-foreground hover:text-foreground"
            )}
          >
            <List className="h-3 w-3" aria-hidden="true" /> Table
          </button>
          <button
            id="view-toggle-dossier"
            onClick={() => setView("dossier")}
            aria-pressed={view === "dossier"}
            className={cn(
              "inline-flex items-center gap-1 px-2 py-1 rounded-sm text-[10px] font-mono transition-colors",
              view === "dossier" ? "bg-surface-3 text-foreground" : "text-muted-foreground hover:text-foreground"
            )}
          >
            <LayoutGrid className="h-3 w-3" aria-hidden="true" /> Dossier
          </button>
        </div>
      </div>

      {/* Dossier grid — 3 columns per row on md+ */}
      {view === "dossier" && (
        <div className="p-4 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2.5">
          {items.map((i) => (
            <IdentifierDossierCard key={i.id} item={i} />
          ))}
        </div>
      )}

      {/* Table view */}
      {view === "table" && (
        <div className="overflow-x-auto">
          <table className="w-full text-xs font-mono">
            <thead>
              <tr className="text-left text-[10px] uppercase font-mono tracking-widest text-muted-foreground border-b border-border bg-surface-2/60">
                <th scope="col" className="px-4 py-2.5 font-semibold">Entity Type</th>
                <th scope="col" className="px-4 py-2.5 font-semibold">Value</th>
                <th scope="col" className="px-4 py-2.5 font-semibold">Confidence</th>
                {hasProfileLinks && (
                  <th scope="col" className="px-4 py-2.5 font-semibold">Profile</th>
                )}
              </tr>
            </thead>
            <tbody className="divide-y divide-border/40">
              {items.map((i) => {
                const Icon = typeIcon[i.type] || Server;
                const displayType = i.platformDisplayName || i.type;

                const isDomainUrl =
                  i.type === "domain" &&
                  i.value.includes(".") &&
                  !i.value.startsWith("Yes") &&
                  !i.value.startsWith("No");

                const valueCell = isDomainUrl ? (
                  <WebsiteIdentifierBadge url={i.value} id={`domain-link-${i.id}`} />
                ) : (
                  <span className="font-mono text-xs text-foreground break-all">{i.value}</span>
                );

                // Simple link for table profile column
                let profileCell: React.ReactNode = null;
                if (i.profileUrl) {
                  const { href, domain, handle } = parseUrl(i.profileUrl);
                  const shortLabel = handle ? `@${handle}` : domain;
                  profileCell = (
                    <a
                      href={href}
                      target="_blank"
                      rel="noopener noreferrer"
                      id={`view-profile-${i.id}`}
                      aria-label={`Open profile ${shortLabel}`}
                      className="inline-flex items-center gap-1 text-[11px] font-mono font-medium text-primary hover:underline"
                    >
                      <ExternalLink className="h-3 w-3 shrink-0" aria-hidden="true" />
                      {shortLabel}
                    </a>
                  );
                }

                return (
                  <tr key={i.id} className="hover:bg-surface-3/50 transition-colors">
                    <td className="px-4 py-2.5 font-sans">
                      <div className="flex items-center gap-2">
                        <div className="h-6 w-6 rounded-sm bg-surface-3 border border-border text-primary grid place-items-center shrink-0" aria-hidden="true">
                          <Icon className="h-3 w-3" />
                        </div>
                        <span className="text-xs uppercase font-mono tracking-wider text-muted-foreground">{displayType}</span>
                      </div>
                    </td>
                    <td className="px-4 py-2.5">{valueCell}</td>
                    <td className="px-4 py-2.5 w-48">
                      <ConfidenceBar value={i.confidence} ariaLabel={`Confidence for ${i.value}`} />
                    </td>
                    {hasProfileLinks && (
                      <td className="px-4 py-2.5 font-sans">
                        {profileCell ?? <span className="text-xs text-muted-foreground/40">—</span>}
                      </td>
                    )}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
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
    success: { icon: CheckCircle2, color: "text-success", bg: "bg-success/10 border-success/30", label: "SUCCESS" },
    failed: { icon: XCircle, color: "text-destructive", bg: "bg-destructive/10 border-destructive/30", label: "FAILED" },
    running: { icon: Loader2, color: "text-primary", bg: "bg-primary/10 border-primary/30", label: "RUNNING" },
    queued: { icon: Clock, color: "text-muted-foreground", bg: "bg-surface-2 border-border", label: "QUEUED" },
  };

  const cfg = statusConfig[c.status as keyof typeof statusConfig] ?? statusConfig.queued;
  const Icon = cfg.icon;

  return (
    <Card
      className={cn(
        "p-3.5 border-border bg-surface rounded-md flex flex-col gap-2.5",
        c.status === "failed" && "border-destructive/40"
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="text-[9px] uppercase font-mono tracking-widest text-muted-foreground">{c.category}</div>
          <div className="font-semibold text-xs text-foreground truncate mt-0.5">{c.name}</div>
        </div>
        <div className={cn("h-6 w-6 rounded-sm border grid place-items-center shrink-0", cfg.bg)} aria-hidden="true">
          <Icon className={cn("h-3 w-3", cfg.color, c.status === "running" && "animate-spin")} />
        </div>
      </div>

      {/* Stats row */}
      <div className="flex items-center justify-between text-xs font-mono text-muted-foreground">
        <span>Hits: <strong className="text-foreground">{c.hits}</strong></span>
        <span>Runtime: <strong className="text-foreground">{c.runtime}</strong></span>
        <span className={cn("text-[9px] font-bold px-1.5 py-0.5 rounded-sm border", cfg.bg, cfg.color)}>
          {cfg.label}
        </span>
      </div>

      {/* Running progress bar */}
      {c.status === "running" && (
        <div
          className="h-1 bg-surface-3 rounded-sm overflow-hidden"
          role="progressbar"
          aria-label={`${c.name} running`}
        >
          <div className="h-full w-1/2 bg-primary animate-pulse" />
        </div>
      )}

      {/* Actions */}
      <div className="pt-1">
        <Button
          size="sm"
          variant="ghost"
          className="h-6 gap-1 text-[11px] font-mono w-full justify-center"
          onClick={onRetry}
          disabled={isRetrying}
          aria-label={`Retry ${c.name}`}
        >
          {isRetrying ? (
            <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" />
          ) : (
            <RotateCcw className="h-3 w-3" aria-hidden="true" />
          )}
          {isRetrying ? "Running…" : "Re-run Connector"}
        </Button>
      </div>
    </Card>
  );
}

// ─── Skeleton loader for connector cards ─────────────────────────────────────

function ConnectorCardSkeleton() {
  return (
    <Card className="p-3.5 border-border bg-surface rounded-md animate-pulse">
      <div className="flex items-start justify-between">
        <div className="space-y-2">
          <div className="h-2 w-16 rounded bg-surface-3" />
          <div className="h-3 w-28 rounded bg-surface-3" />
        </div>
        <div className="h-6 w-6 rounded bg-surface-3" />
      </div>
      <div className="mt-3 flex gap-3">
        <div className="h-3 w-16 rounded bg-surface-3" />
        <div className="h-3 w-20 rounded bg-surface-3" />
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
    if (/^(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}$|^(?:[0-9A-Fa-f]{4}\.){2}[0-9A-Fa-f]{4}$|^[0-9A-Fa-f]{12}$/.test(cleaned)) return "mac";
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
        <AppShell title="Case Not Found">
          <EmptyState
            title="This case record does not exist"
            description={`No investigation matches ID: ${id}.`}
            action={
              <Link to="/investigations">
                <Button size="sm" variant="secondary" className="gap-1.5 text-xs font-mono">
                  <ArrowLeft className="h-3.5 w-3.5" aria-hidden="true" /> ALL_CASES
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
              <span className="font-mono text-xs">
                CASE_ID: {inv.id} · SEED_TARGET: <strong className="text-foreground">{inv.target || "—"}</strong>
              </span>
            }
            actions={
              <div className="flex items-center gap-2">
                <Link to="/investigations">
                  <Button variant="ghost" size="sm" className="gap-1 text-xs font-mono">
                    <ArrowLeft className="h-3.5 w-3.5" aria-hidden="true" /> ALL_CASES
                  </Button>
                </Link>
                <Button
                  variant="secondary"
                  size="sm"
                  className="gap-1 text-xs font-mono border-border bg-surface-2"
                  onClick={() => {
                    invRes.refetch?.();
                    identifiersRes.refetch?.();
                    connectorsRes.refetch?.();
                  }}
                >
                  <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" /> REFRESH
                </Button>
                <Button
                  size="sm"
                  onClick={() => handleExecute(inv)}
                  disabled={execute.isPending || !inv.target}
                  className="gap-1.5 bg-primary text-primary-foreground hover:bg-primary/90 text-xs font-mono"
                >
                  <Play className="h-3.5 w-3.5" aria-hidden="true" />
                  {execute.isPending ? "EXECUTING…" : "EXECUTE ALL"}
                </Button>
              </div>
            }
          >
            {/* Execution error banner */}
            {execute.error && (
              <Card className="border-destructive/40 bg-destructive/10 p-3 mb-3" role="alert">
                <div className="flex items-center gap-2.5 text-xs">
                  <AlertTriangle className="h-4 w-4 text-destructive shrink-0" aria-hidden="true" />
                  <div>
                    <div className="font-mono font-bold text-destructive">EXECUTION_ERROR</div>
                    <div className="text-muted-foreground mt-0.5 font-mono">{execute.error.message}</div>
                  </div>
                  <Button variant="ghost" size="sm" className="ml-auto text-xs font-mono" onClick={() => execute.reset()}>
                    DISMISS
                  </Button>
                </div>
              </Card>
            )}

            {/* Execution success banner */}
            {execute.data && !execute.isPending && !execute.error && (
              <Card className="border-primary/40 bg-primary/5 p-3 mb-3">
                <div className="flex items-center gap-2.5 text-xs font-mono">
                  <CheckCircle2 className="h-4 w-4 text-primary shrink-0" aria-hidden="true" />
                  <div className="flex-1">
                    <div className="font-bold text-foreground">
                      EXECUTION_{execute.data.status === "completed" ? "SUCCESS" : execute.data.status.toUpperCase()}
                    </div>
                    {execute.data.statistics && (
                      <div className="text-muted-foreground mt-0.5 flex gap-3 flex-wrap text-[11px]">
                        <span>Connectors: {execute.data.statistics.executedConnectors}</span>
                        <span className="text-success">OK: {execute.data.statistics.successfulConnectors}</span>
                        {execute.data.statistics.failedConnectors > 0 && (
                          <span className="text-destructive">Fail: {execute.data.statistics.failedConnectors}</span>
                        )}
                        <span>Facts: {execute.data.statistics.normalizedFactsCount}</span>
                        {execute.data.statistics.executionDurationSeconds != null && (
                          <span>Duration: {execute.data.statistics.executionDurationSeconds.toFixed(1)}s</span>
                        )}
                      </div>
                    )}
                  </div>
                  <Button variant="ghost" size="sm" className="text-xs font-mono" onClick={() => execute.reset()}>
                    DISMISS
                  </Button>
                </div>
              </Card>
            )}

            {/* Overview */}
            <div className="grid grid-cols-1 lg:grid-cols-4 gap-3">
              <Card className="p-4 border-border bg-surface rounded-md lg:col-span-3">
                <div className="flex flex-wrap items-center gap-2 pb-3 border-b border-border/60">
                  <StatusBadge status={inv.status} />
                  <SeverityBadge severity={inv.severity} />
                  {inv.tags.map((t) => (
                    <span
                      key={t}
                      className="text-[10px] font-mono px-2 py-0.5 rounded-sm bg-surface-2 text-muted-foreground border border-border"
                    >
                      #{t}
                    </span>
                  ))}
                  <div className="ml-auto text-xs font-mono text-muted-foreground">
                    Analyst: <span className="text-foreground">{inv.owner}</span> · Updated {fmtDate(inv.updatedAt)}
                  </div>
                </div>
                <div className="mt-3 grid grid-cols-2 md:grid-cols-4 gap-3 font-mono">
                  {[
                    { label: "PROGRESS", value: `${derivedProgress}%` },
                    { label: "IDENTIFIERS", value: identifiersRes.data?.length ?? inv.identifiers },
                    { label: "CONNECTORS", value: connectorsRes.data?.length ?? inv.connectors },
                    { label: "CREATED", value: fmtDate(inv.createdAt) },
                  ].map((m) => (
                    <div key={m.label} className="p-2 rounded-sm bg-surface-2 border border-border">
                      <div className="text-[9px] uppercase tracking-widest text-muted-foreground">{m.label}</div>
                      <div className="text-sm font-bold text-foreground mt-0.5">{m.value}</div>
                    </div>
                  ))}
                </div>
                <Progress value={derivedProgress} className="h-1 bg-surface-3 mt-3" />
              </Card>

              <Card className="p-4 border-border bg-surface rounded-md">
                <h3 className="font-display text-xs font-bold uppercase tracking-wider text-foreground pb-2 border-b border-border/60">
                  Workspace Views
                </h3>
                <div className="mt-2 space-y-1">
                  {jumpLinks.map((l) => (
                    <Link
                      key={l.label}
                      to={l.to}
                      className="flex items-center gap-2 p-1.5 rounded-sm hover:bg-surface-2 text-xs font-mono text-muted-foreground hover:text-foreground transition"
                    >
                      <l.icon className="h-3.5 w-3.5 text-primary shrink-0" aria-hidden="true" />
                      {l.label}
                    </Link>
                  ))}
                </div>
              </Card>
            </div>

            {/* Tabs */}
            <Tabs defaultValue="identifiers" className="mt-4">
              <TabsList className="bg-surface-2 border border-border h-9 p-1 rounded-sm font-mono text-xs">
                <TabsTrigger value="identifiers" className="h-7 text-xs rounded-sm">
                  Identifiers ({identifiersRes.data?.length ?? 0})
                </TabsTrigger>
                <TabsTrigger value="connectors" className="h-7 text-xs rounded-sm">
                  Connectors ({connectorsRes.data?.length ?? 0})
                </TabsTrigger>
                <TabsTrigger value="execution" className="h-7 text-xs rounded-sm">Execution Log</TabsTrigger>
                <TabsTrigger value="activity" className="h-7 text-xs rounded-sm">Activity</TabsTrigger>
              </TabsList>

              {/* Identifiers tab */}
              <TabsContent value="identifiers" className="mt-2">
                <Card className="border-border bg-surface rounded-md overflow-hidden">
                  <AsyncBoundary
                    resource={identifiersRes}
                    isEmpty={(items) => items.length === 0}
                  >
                    {(items) => <IdentifierTable items={items} />}
                  </AsyncBoundary>
                </Card>
              </TabsContent>

              {/* Connectors tab */}
              <TabsContent value="connectors" className="mt-2">
                {connectorsRes.isLoading ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-2">
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
                      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-2">
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
              <TabsContent value="execution" className="mt-2">
                <Card className="p-4 border-border bg-surface rounded-md">
                  <h3 className="font-display text-xs font-bold uppercase tracking-wider text-foreground pb-2 mb-3 border-b border-border/60">
                    Execution Step Log
                  </h3>
                  {execute.data?.connectorResults && execute.data.connectorResults.length > 0 ? (
                    <ConnectorTimeline results={execute.data.connectorResults} />
                  ) : (
                    <EmptyState
                      title="No execution log recorded"
                      description="Click Execute All to trigger per-connector execution logs."
                      action={
                        <Button
                          size="sm"
                          onClick={() => handleExecute(inv)}
                          disabled={execute.isPending || !inv.target}
                          className="gap-1.5 bg-primary text-primary-foreground font-mono text-xs"
                        >
                          <Play className="h-3.5 w-3.5" aria-hidden="true" /> Run Execution
                        </Button>
                      }
                    />
                  )}
                </Card>
              </TabsContent>

              {/* Activity tab */}
              <TabsContent value="activity" className="mt-2">
                <Card className="p-4 border-border bg-surface rounded-md text-xs text-muted-foreground font-mono">
                  Full chronological event log available in the{" "}
                  <Link to="/timeline" className="text-primary hover:underline">Timeline View</Link>.
                </Card>
              </TabsContent>
            </Tabs>
          </AppShell>
        );
      }}
    </AsyncBoundary>
  );
}

