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
  head: () => ({ meta: [{ title: "Identity Profile — AXIOM OSINT" }] }),
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
          // Fetch identifiers for up to 10 most recent investigations to avoid spamming the backend
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
      title="Analyst Identity"
      subtitle="Overview of your account and recent investigation activity"
    >
      <AsyncBoundary resource={invRes}>
        {(investigations) => (
          <>
            {/* Subject header */}
            <Card className="glass border-border/60 overflow-hidden mb-6">
              <div className="relative p-6">
                <div className="absolute inset-0 opacity-30 gradient-text" aria-hidden="true" />
                <div className="relative flex flex-wrap items-center gap-4">
                  <div className="relative">
                    <div className="absolute inset-0 rounded-full blur-lg opacity-70 bg-gradient-to-br from-primary to-accent" aria-hidden="true" />
                    <div className="relative h-16 w-16 rounded-full bg-gradient-to-br from-primary to-accent grid place-items-center text-2xl font-display font-bold text-primary-foreground">
                      {user?.email ? user.email[0].toUpperCase() : "A"}
                    </div>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-xs uppercase tracking-widest text-muted-foreground">Account Profile</div>
                    <div className="text-xl font-display font-semibold">
                      {user?.fullName || "Authenticated Analyst"}
                    </div>
                    {user?.email && (
                      <div className="text-xs text-muted-foreground font-mono mt-0.5 flex items-center gap-2">
                        <Mail className="h-3 w-3" aria-hidden="true" />
                        {user.email}
                      </div>
                    )}
                  </div>
                  <div className="flex flex-wrap gap-2 mt-4 md:mt-0">
                    <MetricPill label="Total Investigations" value={String(investigations.length)} />
                    <MetricPill 
                      label="Identifiers (Recent)" 
                      value={loadingIds ? "..." : String(identifiers.length)} 
                    />
                    <MetricPill 
                      label="Avg Confidence" 
                      value={loadingIds ? "..." : `${avgConfidence}%`} 
                      tone={avgConfidence > 70 ? "success" : undefined} 
                    />
                  </div>
                </div>
              </div>
            </Card>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2">
                <div className="flex items-center gap-2 mb-4">
                  <Activity className="h-4 w-4 text-primary" aria-hidden="true" />
                  <h3 className="font-display font-semibold">Recent Investigations</h3>
                </div>

                {investigations.length === 0 ? (
                  <Card className="glass p-8 border-border/60 text-center flex flex-col items-center">
                    <div className="h-10 w-10 rounded-lg bg-white/5 grid place-items-center text-muted-foreground mb-3">
                      <Inbox className="h-5 w-5" aria-hidden="true" />
                    </div>
                    <h4 className="text-sm font-medium">No investigations yet</h4>
                    <p className="text-xs text-muted-foreground max-w-sm mt-1">
                      You haven't created any investigations. Run a new investigation from the dashboard to see it here.
                    </p>
                  </Card>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {investigations.slice(0, 6).map(inv => (
                      <Card key={inv.id} className="glass p-4 border-border/60 hover:bg-white/[0.04] transition-colors">
                        <Link to="/investigations/$id" params={{ id: inv.id }} className="block">
                          <div className="flex justify-between items-start mb-2">
                            <h4 className="font-display font-medium text-sm truncate max-w-[140px]">{inv.name}</h4>
                            <span className={`text-[9px] px-2 py-0.5 rounded-full uppercase tracking-widest font-medium ${
                              inv.status === 'completed' ? 'bg-emerald-500/10 text-emerald-500' :
                              inv.status === 'active' ? 'bg-blue-500/10 text-blue-500' :
                              inv.status === 'failed' ? 'bg-red-500/10 text-red-500' :
                              'bg-primary/10 text-primary'
                            }`}>
                              {inv.status}
                            </span>
                          </div>
                          <div className="space-y-1.5 mt-3">
                            <div className="text-[11px] text-muted-foreground flex items-center gap-2">
                              <Target className="h-3 w-3" />
                              <span className="truncate">{inv.target}</span>
                            </div>
                            <div className="text-[11px] text-muted-foreground flex items-center gap-2">
                              <Calendar className="h-3 w-3" />
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
                <div className="flex items-center gap-2 mb-4">
                  <Fingerprint className="h-4 w-4 text-primary" aria-hidden="true" />
                  <h3 className="font-display font-semibold">Identifier Summary</h3>
                </div>

                <Card className="glass p-5 border-border/60">
                  {loadingIds ? (
                    <div className="text-xs text-muted-foreground text-center py-6">
                      Loading identifier statistics...
                    </div>
                  ) : identifiers.length === 0 ? (
                    <div className="text-xs text-muted-foreground text-center py-6">
                      No identifiers discovered yet.
                    </div>
                  ) : (
                    <div className="space-y-4">
                      <div className="flex justify-between items-center pb-3 border-b border-border/40">
                        <span className="text-xs text-muted-foreground">Total Discovered</span>
                        <span className="font-mono text-sm">{identifiers.length}</span>
                      </div>
                      <div className="flex justify-between items-center pb-3 border-b border-border/40">
                        <span className="text-xs text-muted-foreground">Unique Types</span>
                        <span className="font-mono text-sm">{uniqueIdTypes}</span>
                      </div>
                      
                      <div className="pt-2 space-y-2">
                        <span className="text-[10px] uppercase tracking-widest text-muted-foreground">Distribution</span>
                        {Object.entries(identifierTypes)
                          .sort(([,a], [,b]) => b - a)
                          .map(([type, count]) => (
                          <div key={type} className="flex justify-between items-center text-xs">
                            <span className="capitalize">{type}</span>
                            <span className="font-mono">{count}</span>
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
