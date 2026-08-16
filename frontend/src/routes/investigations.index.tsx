import { createFileRoute, Link, redirect } from "@tanstack/react-router";
import { useMemo, useState, useCallback } from "react";
import { AppShell } from "@/components/app-shell";
import { StatusBadge, SeverityBadge } from "@/components/badges";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Search, Plus, Filter, ChevronLeft, ChevronRight, ArrowUpDown, Trash2 } from "lucide-react";
import { AsyncBoundary, EmptyState } from "@/components/states";
import { useInvestigations, useDeleteInvestigation } from "@/hooks/use-osint-data";
import { fmtDate } from "@/lib/format";
import { isAuthenticated } from "@/lib/auth";
import { ConfirmationModal } from "@/components/ui/confirmation-modal";
import type { Investigation, InvestigationStatus, Severity } from "@/types/domain";

export const Route = createFileRoute("/investigations/")({
  beforeLoad: () => {
    if (!isAuthenticated()) throw redirect({ to: "/auth" });
  },
  head: () => ({ meta: [{ title: "Investigations — AXIOM OSINT" }] }),
  component: List,
});

type StatusFilter = "all" | InvestigationStatus;
type SortKey = "recent" | "name" | "severity";

const SEVERITY_WEIGHT: Record<Severity, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
};

function applyFilters(
  data: Investigation[],
  query: string,
  status: StatusFilter,
  sort: SortKey,
): Investigation[] {
  let list = data.filter(
    (i) =>
      (status === "all" || i.status === status) &&
      (query === "" ||
        i.name.toLowerCase().includes(query.toLowerCase()) ||
        i.target.toLowerCase().includes(query.toLowerCase()) ||
        i.id.toLowerCase().includes(query.toLowerCase())),
  );
  if (sort === "name") list = [...list].sort((a, b) => a.name.localeCompare(b.name));
  if (sort === "severity")
    list = [...list].sort(
      (a, b) => SEVERITY_WEIGHT[a.severity] - SEVERITY_WEIGHT[b.severity],
    );
  if (sort === "recent")
    list = [...list].sort(
      (a, b) => +new Date(b.updatedAt) - +new Date(a.updatedAt),
    );
  return list;
}

function List() {
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState<StatusFilter>("all");
  const [sort, setSort] = useState<SortKey>("recent");
  const [deleteTarget, setDeleteTarget] = useState<Investigation | null>(null);
  const resource = useInvestigations();
  const deleteInv = useDeleteInvestigation();
  const all = resource.data ?? [];
  const filtered = useMemo(
    () => applyFilters(all, query, status, sort),
    [all, query, status, sort],
  );

  const handleDeleteConfirm = useCallback(async () => {
    if (!deleteTarget) return;
    try {
      await deleteInv.mutate(deleteTarget.id);
      resource.refetch?.();
    } catch { /* error surfaced via deleteInv.error */ }
    finally { setDeleteTarget(null); }
  }, [deleteTarget, deleteInv, resource]);

  return (
    <AppShell
      title="Investigation Registry"
      subtitle={`${filtered.length} of ${all.length} registered cases`}
      actions={
        <Link to="/investigations/new">
          <Button size="sm" className="bg-primary text-primary-foreground hover:bg-primary/90 gap-1.5 text-xs font-medium rounded-sm">
            <Plus className="h-3.5 w-3.5" aria-hidden="true" /> New Investigation
          </Button>
        </Link>
      }
    >
      {/* Delete confirmation modal */}
      <ConfirmationModal
        open={!!deleteTarget}
        title="Delete investigation?"
        description={
          <>
            <strong className="text-foreground">{deleteTarget?.name}</strong> will be permanently deleted
            along with all its connector results, identifiers, and facts.
            This action cannot be undone.
          </>
        }
        confirmLabel="Delete"
        destructive
        isPending={deleteInv.isPending}
        onConfirm={handleDeleteConfirm}
        onCancel={() => setDeleteTarget(null)}
      />

      <Card className="p-3 border-border bg-surface rounded-md">
        <div className="flex flex-wrap items-center gap-2.5">
          <div className="relative flex-1 min-w-[220px]">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />
            <label className="sr-only" htmlFor="inv-search">Filter investigations</label>
            <Input
              id="inv-search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Filter by case name, target, ID…"
              className="h-8 pl-8 text-xs bg-surface-2 border-border font-mono"
            />
          </div>
          <Select value={status} onValueChange={(v) => setStatus(v as StatusFilter)}>
            <SelectTrigger className="w-[150px] h-8 text-xs bg-surface-2 border-border" aria-label="Status filter">
              <Filter className="h-3.5 w-3.5 mr-1.5 text-muted-foreground" aria-hidden="true" /><SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All statuses</SelectItem>
              <SelectItem value="active">Active</SelectItem>
              <SelectItem value="pending">Pending</SelectItem>
              <SelectItem value="completed">Completed</SelectItem>
              <SelectItem value="failed">Failed</SelectItem>
            </SelectContent>
          </Select>
          <Select value={sort} onValueChange={(v) => setSort(v as SortKey)}>
            <SelectTrigger className="w-[160px] h-8 text-xs bg-surface-2 border-border" aria-label="Sort order">
              <ArrowUpDown className="h-3.5 w-3.5 mr-1.5 text-muted-foreground" aria-hidden="true" /><SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="recent">Recently updated</SelectItem>
              <SelectItem value="name">Name A–Z</SelectItem>
              <SelectItem value="severity">Severity</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </Card>

      <Card className="mt-3 border-border bg-surface rounded-md overflow-hidden">
        <AsyncBoundary resource={resource}>
          {() => (
            <>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-left text-[10px] uppercase font-mono tracking-widest text-muted-foreground border-b border-border bg-surface-2/60">
                      <th scope="col" className="px-4 py-2.5 font-semibold">Case Title</th>
                      <th scope="col" className="px-4 py-2.5 font-semibold">Target Entity</th>
                      <th scope="col" className="px-4 py-2.5 font-semibold">Severity</th>
                      <th scope="col" className="px-4 py-2.5 font-semibold">Status</th>
                      <th scope="col" className="px-4 py-2.5 font-semibold">Connectors Progress</th>
                      <th scope="col" className="px-4 py-2.5 font-semibold">Analyst</th>
                      <th scope="col" className="px-4 py-2.5 font-semibold">Updated</th>
                      <th scope="col" className="px-4 py-2.5 font-semibold sr-only">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/40 font-mono">
                    {filtered.map((inv) => (
                      <tr key={inv.id} className="hover:bg-surface-3/50 transition-colors group">
                        <td className="px-4 py-2.5 font-sans">
                          <Link to="/investigations/$id" params={{ id: inv.id }} className="flex items-center gap-2.5">
                            <div className="h-6 px-1.5 rounded-sm bg-surface-3 border border-border grid place-items-center text-[10px] font-mono text-primary font-bold">
                              {inv.id.split("-")[1]}
                            </div>
                            <div>
                              <div className="font-semibold text-foreground hover:text-primary transition-colors">{inv.name}</div>
                              <div className="text-[10px] text-muted-foreground font-mono">{inv.id}</div>
                            </div>
                          </Link>
                        </td>
                        <td className="px-4 py-2.5 font-mono text-xs text-foreground/90">{inv.target}</td>
                        <td className="px-4 py-2.5"><SeverityBadge severity={inv.severity} /></td>
                        <td className="px-4 py-2.5"><StatusBadge status={inv.status} /></td>
                        <td className="px-4 py-2.5 w-44">
                          <Progress value={inv.progress} className="h-1 bg-surface-3" />
                          <div className="text-[10px] text-muted-foreground mt-1 font-mono">
                            {inv.progress}% · {inv.identifiers} ids
                          </div>
                        </td>
                        <td className="px-4 py-2.5 text-xs text-muted-foreground font-sans">{inv.owner}</td>
                        <td className="px-4 py-2.5 text-[11px] text-muted-foreground font-mono">{fmtDate(inv.updatedAt)}</td>
                        <td className="px-4 py-2.5 text-right">
                          <Button
                            variant="ghost"
                            size="icon"
                            aria-label={`Delete ${inv.name}`}
                            className="h-6 w-6 opacity-0 group-hover:opacity-100 transition text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                            onClick={() => setDeleteTarget(inv)}
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        </td>
                      </tr>
                    ))}
                    {filtered.length === 0 && (
                      <tr>
                        <td colSpan={8} className="px-5 py-12 text-center text-muted-foreground">
                          <EmptyState
                            title="No investigations match your filters."
                            description="Adjust your search or clear filters to see more results."
                          />
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
              <div className="flex items-center justify-between px-4 py-2.5 border-t border-border text-xs text-muted-foreground font-mono bg-surface-2/30">
                <div>LOG_COUNT: 1–{filtered.length} of {all.length}</div>
                <nav aria-label="Pagination" className="flex items-center gap-1">
                  <Button variant="ghost" size="sm" disabled aria-label="Previous page" className="h-7 w-7 p-0">
                    <ChevronLeft className="h-3.5 w-3.5" aria-hidden="true" />
                  </Button>
                  <Button variant="ghost" size="sm" className="h-7 w-7 p-0 text-primary font-bold" aria-current="page">1</Button>
                  <Button variant="ghost" size="sm" className="h-7 w-7 p-0">2</Button>
                  <Button variant="ghost" size="sm" className="h-7 w-7 p-0">3</Button>
                  <Button variant="ghost" size="sm" aria-label="Next page" className="h-7 w-7 p-0">
                    <ChevronRight className="h-3.5 w-3.5" aria-hidden="true" />
                  </Button>
                </nav>
              </div>
            </>
          )}
        </AsyncBoundary>
      </Card>
    </AppShell>
  );
}

