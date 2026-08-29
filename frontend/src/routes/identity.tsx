import { useState, useEffect, useMemo } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { AppShell } from "@/components/app-shell";
import { Card } from "@/components/ui/card";
import { Mail, Target, Calendar, Fingerprint, Activity, Inbox } from "lucide-react";
import { AsyncBoundary, EmptyState } from "@/components/states";
import { MetricPill } from "@/components/field";
import { formatConfidencePercent } from "@/components/confidence-bar";
import { useInvestigations } from "@/hooks/use-osint-data";
import { getUser } from "@/lib/auth";
import { getDataProvider } from "@/lib/api/data-provider";
import { Identifier } from "@/types/domain";

export const Route = createFileRoute("/identity")({
  head: () => ({ meta: [{ title: "Identity Profile — IntelWeave" }] }),
  component: Identity,
});

function Identity() {
  const invRes = useInvestigations();
  const user = getUser();

  const [identifiers, setIdentifiers] = useState<Identifier[]>([]);
  const [loadingIds, setLoadingIds] = useState(false);

  useEffect(() => {
    if (invRes.data && invRes.data.length > 0) {
      let cancelled = false;
      setLoadingIds(true);
      
      const fetchAll = async () => {
        try {
          const provider = getDataProvider();
          const recentInvs = invRes.data?.slice(0, 10) || [];
          const allIds = await Promise.all(
            recentInvs.map(inv => provider.listIdentifiers(inv.id).catch(() => []))
          );
          if (!cancelled) {
            setIdentifiers(allIds.flat());
            setLoadingIds(false);
          }
        } catch (e) {
          if (!cancelled) setLoadingIds(false);
        }
      };
      
      fetchAll();
      return () => { cancelled = true; };
    }
  }, [invRes.data]);

  const uniqueIdTypes = new Set(identifiers.map(i => i.type)).size;
  const avgConfidence = useMemo(() => {
    if (identifiers.length === 0) return 0;
    const total = identifiers.reduce((acc, curr) => acc + formatConfidencePercent(curr.confidence), 0);
    return Math.round(total / identifiers.length);
  }, [identifiers]);

  const identifierTypes = useMemo(() => {
    return identifiers.reduce((acc, curr) => {
      acc[curr.type] = (acc[curr.type] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);
  }, [identifiers]);

  return (
    <AppShell
      title="Analyst Profile & Identity Metrics"
      subtitle="Overview of authenticated analyst account and enriched case telemetry"
    >
      <AsyncBoundary resource={invRes}>
        {(investigations) => (
          <>
            {/* Subject header */}
            <Card className="p-4 border-border bg-surface rounded-md mb-4">
              <div className="flex flex-wrap items-center gap-4">
                <div className="h-12 w-12 rounded-sm bg-surface-2 border border-border grid place-items-center text-xl font-mono font-bold text-primary shrink-0">
                  {user?.email ? user.email[0].toUpperCase() : "A"}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-[9px] uppercase font-mono tracking-widest text-muted-foreground">Analyst Record</div>
                  <div className="text-base font-display font-semibold text-foreground">
                    {user?.fullName || "Authenticated Analyst"}
                  </div>
                  {user?.email && (
                    <div className="text-xs text-muted-foreground font-mono mt-0.5 flex items-center gap-1.5">
                      <Mail className="h-3 w-3" aria-hidden="true" />
                      {user.email}
                    </div>
                  )}
                </div>
                <div className="flex flex-wrap gap-2">
                  <MetricPill label="Total Cases" value={String(investigations.length)} />
                  <MetricPill 
                    label="Discovered Entities" 
                    value={loadingIds ? "..." : String(identifiers.length)} 
                  />
                  <MetricPill 
                    label="Avg Confidence" 
                    value={loadingIds ? "..." : `${avgConfidence}%`} 
                    tone={avgConfidence > 70 ? "success" : undefined} 
                  />
                </div>
              </div>
            </Card>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
              <div className="lg:col-span-2">
                <div className="flex items-center gap-2 mb-2 pb-2 border-b border-border/60">
                  <Activity className="h-3.5 w-3.5 text-primary" aria-hidden="true" />
                  <h3 className="font-display text-xs font-bold uppercase tracking-wider text-foreground">Assigned Investigations</h3>
                </div>

                {investigations.length === 0 ? (
                  <Card className="p-6 border-border bg-surface text-center flex flex-col items-center">
                    <div className="h-8 w-8 rounded-sm bg-surface-2 border border-border grid place-items-center text-muted-foreground mb-2">
                      <Inbox className="h-4 w-4" aria-hidden="true" />
                    </div>
                    <h4 className="text-xs font-medium">No investigations assigned</h4>
                    <p className="text-xs text-muted-foreground mt-1">
                      Create an investigation from the toolbar to see case telemetry here.
                    </p>
                  </Card>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
                    {investigations.slice(0, 6).map(inv => (
                      <Card key={inv.id} className="p-3 border-border bg-surface hover:bg-surface-2 transition-colors">
                        <Link to="/investigations/$id" params={{ id: inv.id }} className="block">
                          <div className="flex justify-between items-start mb-2">
                            <h4 className="font-semibold text-xs text-foreground truncate max-w-[140px] font-sans">{inv.name}</h4>
                            <span className="text-[9px] font-mono font-bold uppercase px-1.5 py-0.5 rounded-sm border border-border bg-surface-2 text-muted-foreground">
                              {inv.status}
                            </span>
                          </div>
                          <div className="space-y-1 mt-2 text-[11px] font-mono text-muted-foreground">
                            <div className="flex items-center gap-1.5">
                              <Target className="h-3 w-3 shrink-0" />
                              <span className="truncate">{inv.target}</span>
                            </div>
                            <div className="flex items-center gap-1.5">
                              <Calendar className="h-3 w-3 shrink-0" />
                              <span>{new Date(inv.createdAt).toLocaleDateString()}</span>
                            </div>
                          </div>
                        </Link>
                      </Card>
                    ))}
                  </div>
                )}
              </div>

              <div>
                <div className="flex items-center gap-2 mb-2 pb-2 border-b border-border/60">
                  <Fingerprint className="h-3.5 w-3.5 text-primary" aria-hidden="true" />
                  <h3 className="font-display text-xs font-bold uppercase tracking-wider text-foreground">Entity Type Telemetry</h3>
                </div>

                <Card className="p-4 border-border bg-surface rounded-md">
                  {loadingIds ? (
                    <div className="text-xs font-mono text-muted-foreground text-center py-4">
                      Loading telemetry metrics...
                    </div>
                  ) : identifiers.length === 0 ? (
                    <div className="text-xs font-mono text-muted-foreground text-center py-4">
                      No entity identifiers gathered.
                    </div>
                  ) : (
                    <div className="space-y-3 font-mono text-xs">
                      <div className="flex justify-between items-center pb-2 border-b border-border/40">
                        <span className="text-muted-foreground">Discovered Identifiers</span>
                        <span className="font-bold text-foreground">{identifiers.length}</span>
                      </div>
                      <div className="flex justify-between items-center pb-2 border-b border-border/40">
                        <span className="text-muted-foreground">Distinct Entity Types</span>
                        <span className="font-bold text-foreground">{uniqueIdTypes}</span>
                      </div>
                      
                      <div className="pt-1 space-y-1.5">
                        <span className="text-[9px] uppercase tracking-widest text-muted-foreground">Breakdown by Type</span>
                        {Object.entries(identifierTypes)
                          .sort(([,a], [,b]) => b - a)
                          .map(([type, count]) => (
                          <div key={type} className="flex justify-between items-center text-xs p-1 rounded-sm bg-surface-2 border border-border/40">
                            <span className="capitalize text-muted-foreground">{type}</span>
                            <span className="font-bold text-foreground">{count}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </Card>
              </div>
            </div>
          </>
        )}
      </AsyncBoundary>
    </AppShell>
  );
}

