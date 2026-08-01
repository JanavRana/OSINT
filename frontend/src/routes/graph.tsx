import { createFileRoute } from "@tanstack/react-router";
import { useCallback, useMemo, useRef, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  Mail, Globe, User, Wallet, Server, ZoomIn, ZoomOut, Maximize2,
  Layers, Search, Network,
} from "lucide-react";
import { AsyncBoundary, EmptyState } from "@/components/states";
import { Field } from "@/components/field";
import { useGraph, useInvestigations } from "@/hooks/use-osint-data";
import { cn } from "@/lib/utils";
import type { GraphData, GraphEdge, GraphNode, GraphNodeType } from "@/types/domain";

export const Route = createFileRoute("/graph")({
  head: () => ({ meta: [{ title: "Graph View — AXIOM OSINT" }] }),
  component: Graph,
});

const iconMap: Record<GraphNodeType, typeof Mail> = {
  email: Mail,
  domain: Globe,
  user: User,
  wallet: Wallet,
  ip: Server,
};

const colorMap: Record<GraphNodeType, string> = {
  email: "text-primary bg-primary/15 border-primary/40",
  domain: "text-accent bg-accent/15 border-accent/40",
  user: "text-warning bg-warning/15 border-warning/40",
  wallet: "text-success bg-success/15 border-success/40",
  ip: "text-destructive bg-destructive/15 border-destructive/40",
};

interface Selection {
  node: GraphNode | null;
  edge: GraphEdge | null;
}

// ─── Draggable Graph Canvas ──────────────────────────────────────────────────

type NodePositions = Map<string, { x: number; y: number }>;

function GraphCanvas({
  data,
  zoom,
  pan,
  positions,
  selection,
  query,
  onSelect,
  onNodeDrag,
}: {
  data: GraphData;
  zoom: number;
  pan: { x: number; y: number };
  positions: NodePositions;
  selection: Selection;
  query: string;
  onSelect: (s: Selection) => void;
  onNodeDrag: (id: string, x: number, y: number) => void;
}) {
  const { nodes, edges } = data;
  const canvasRef = useRef<HTMLDivElement>(null);
  const draggingRef = useRef<{ id: string; startX: number; startY: number; origX: number; origY: number } | null>(null);

  const getPos = (n: GraphNode) => positions.get(n.id) ?? { x: n.x, y: n.y };

  const lowerQ = query.toLowerCase();
  const matchingIds = useMemo(() => {
    if (!lowerQ) return new Set<string>();
    return new Set(nodes.filter((n) => n.label.toLowerCase().includes(lowerQ)).map((n) => n.id));
  }, [nodes, lowerQ]);

  const handleMouseDown = useCallback((e: React.MouseEvent, nodeId: string, currentX: number, currentY: number) => {
    e.preventDefault();
    draggingRef.current = { id: nodeId, startX: e.clientX, startY: e.clientY, origX: currentX, origY: currentY };

    const onMouseMove = (me: MouseEvent) => {
      if (!draggingRef.current || !canvasRef.current) return;
      const rect = canvasRef.current.getBoundingClientRect();
      const dx = (me.clientX - draggingRef.current.startX) / (rect.width * zoom / 100);
      const dy = (me.clientY - draggingRef.current.startY) / (rect.height * zoom / 100);
      onNodeDrag(draggingRef.current.id, draggingRef.current.origX + dx, draggingRef.current.origY + dy);
    };

    const onMouseUp = () => {
      draggingRef.current = null;
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
    };

    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);
  }, [zoom, onNodeDrag]);

  return (
    <div
      ref={canvasRef}
      className="absolute inset-0 overflow-hidden cursor-grab active:cursor-grabbing"
      style={{ transform: `scale(${zoom / 100}) translate(${pan.x}px, ${pan.y}px)`, transformOrigin: "center" }}
    >
      {/* Edges */}
      <svg className="absolute inset-0 h-full w-full pointer-events-none" aria-hidden="true">
        <defs>
          <linearGradient id="edge-grad" x1="0" x2="1">
            <stop offset="0%" stopColor="oklch(0.82 0.17 195)" stopOpacity="0.7" />
            <stop offset="100%" stopColor="oklch(0.65 0.24 295)" stopOpacity="0.7" />
          </linearGradient>
        </defs>
        {edges.map((e, i) => {
          const a = nodes.find((n) => n.id === e.from);
          const b = nodes.find((n) => n.id === e.to);
          if (!a || !b) return null;
          const posA = getPos(a);
          const posB = getPos(b);
          const active = selection.edge === e;
          const highlighted =
            (lowerQ && (matchingIds.has(e.from) || matchingIds.has(e.to))) ||
            (selection.node && (e.from === selection.node.id || e.to === selection.node.id));
          return (
            <line
              key={i}
              x1={`${posA.x}%`} y1={`${posA.y}%`}
              x2={`${posB.x}%`} y2={`${posB.y}%`}
              stroke={active || highlighted ? "oklch(0.82 0.17 195)" : "url(#edge-grad)"}
              strokeWidth={active || highlighted ? 2 : 1}
              strokeDasharray={active ? "0" : "4 4"}
              opacity={lowerQ && !matchingIds.has(e.from) && !matchingIds.has(e.to) ? 0.2 : 1}
              className="pointer-events-auto cursor-pointer transition-opacity"
              onClick={() => onSelect({ node: null, edge: e })}
            />
          );
        })}
      </svg>

      {/* Nodes */}
      {nodes.map((n) => {
        const Icon = iconMap[n.type];
        const size = n.size ?? 26;
        const isSel = selection.node?.id === n.id;
        const isMatch = lowerQ ? matchingIds.has(n.id) : true;
        const pos = getPos(n);

        return (
          <button
            key={n.id}
            className={cn(
              "absolute -translate-x-1/2 -translate-y-1/2 group focus-visible:outline-none transition-opacity",
              !isMatch && lowerQ && "opacity-20"
            )}
            style={{ left: `${pos.x}%`, top: `${pos.y}%` }}
            aria-label={`${n.type} ${n.label}`}
            aria-pressed={isSel}
            onMouseDown={(e) => handleMouseDown(e, n.id, pos.x, pos.y)}
            onClick={() => onSelect({ node: n, edge: null })}
          >
            {n.primary && <div className="absolute inset-0 -m-3 rounded-full bg-primary/30 blur-xl" aria-hidden="true" />}
            {isMatch && lowerQ && (
              <div className="absolute inset-0 -m-2 rounded-full bg-warning/30 blur-md animate-pulse" aria-hidden="true" />
            )}
            <div
              className={cn(
                "relative rounded-full border grid place-items-center transition-all",
                colorMap[n.type],
                isSel && "ring-2 ring-primary ring-offset-2 ring-offset-background scale-110",
                n.primary && "shadow-[0_0_30px_-4px_var(--primary)]",
              )}
              style={{ height: size, width: size }}
              aria-hidden="true"
            >
              <Icon className="h-3.5 w-3.5" />
            </div>
            <div className="mt-1 text-[10px] font-mono text-muted-foreground whitespace-nowrap text-center opacity-80 group-hover:opacity-100 max-w-[80px] truncate">
              {n.label}
            </div>
          </button>
        );
      })}
    </div>
  );
}

function GraphLegend() {
  return (
    <div className="absolute bottom-3 left-3 glass rounded-xl p-3 text-xs">
      <div className="font-medium mb-2">Legend</div>
      <div className="grid grid-cols-2 gap-x-3 gap-y-1">
        {(Object.keys(iconMap) as GraphNodeType[]).map((t) => {
          const Icon = iconMap[t];
          return (
            <div key={t} className="flex items-center gap-1.5 text-muted-foreground">
              <span className={cn("h-4 w-4 rounded-full grid place-items-center border", colorMap[t])} aria-hidden="true">
                <Icon className="h-2.5 w-2.5" />
              </span>
              <span className="capitalize">{t}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function NodeDetails({ node, edges, nodes }: { node: GraphNode; edges: GraphEdge[]; nodes: GraphNode[] }) {
  const Icon = iconMap[node.type];
  const connected = edges.filter((e) => e.from === node.id || e.to === node.id);
  return (
    <div className="mt-4 space-y-4">
      <div className="flex items-center gap-3">
        <div className={cn("h-12 w-12 rounded-full border grid place-items-center", colorMap[node.type])} aria-hidden="true">
          <Icon className="h-5 w-5" />
        </div>
        <div className="min-w-0">
          <div className="text-xs uppercase tracking-widest text-muted-foreground">{node.type}</div>
          <div className="font-mono text-sm truncate max-w-[200px]">{node.label}</div>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3 text-xs">
        <Field label="Connections" value={String(connected.length)} />
        <Field label="Primary" value={node.primary ? "Yes (seed)" : "No"} />
      </div>
      {connected.length > 0 && (
        <div>
          <div className="text-[10px] uppercase tracking-widest text-muted-foreground mb-2">Connected to</div>
          <div className="space-y-1 max-h-40 overflow-y-auto">
            {connected.map((e, i) => {
              const otherId = e.from === node.id ? e.to : e.from;
              const other = nodes.find((n) => n.id === otherId);
              return (
                <div key={i} className="text-xs flex items-center gap-2 p-2 rounded-md bg-white/[0.03]">
                  <span className="h-1.5 w-1.5 rounded-full bg-primary" aria-hidden="true" />
                  <span className="text-muted-foreground">{e.kind}</span>
                  <span className="ml-auto font-mono text-[10px] truncate max-w-[100px]">{other?.label ?? otherId}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

function EdgeDetails({ edge, nodes }: { edge: GraphEdge; nodes: GraphNode[] }) {
  return (
    <div className="mt-4 space-y-3 text-sm">
      <Field label="Relation" value={edge.kind} />
      <Field label="From" value={nodes.find((n) => n.id === edge.from)?.label ?? edge.from} mono />
      <Field label="To" value={nodes.find((n) => n.id === edge.to)?.label ?? edge.to} mono />
    </div>
  );
}

// ─── Main Graph page ──────────────────────────────────────────────────────────

function Graph() {
  const invRes = useInvestigations();
  const [selectedInvId, setSelectedInvId] = useState<string | undefined>(undefined);
  const resource = useGraph(selectedInvId);
  const [zoom, setZoom] = useState(100);
  const [pan] = useState({ x: 0, y: 0 });
  const [selection, setSelection] = useState<Selection>({ node: null, edge: null });
  const [query, setQuery] = useState("");
  const [positions, setPositions] = useState<NodePositions>(new Map());

  const handleNodeDrag = useCallback((id: string, x: number, y: number) => {
    setPositions((prev) => {
      const next = new Map(prev);
      next.set(id, { x: Math.max(5, Math.min(95, x)), y: Math.max(5, Math.min(95, y)) });
      return next;
    });
  }, []);

  // Reset positions when investigation changes
  const handleInvChange = (invId: string) => {
    setSelectedInvId(invId === "__none__" ? undefined : invId);
    setPositions(new Map());
    setSelection({ node: null, edge: null });
    setQuery("");
  };

  const fitToScreen = () => {
    setZoom(100);
    setPositions(new Map());
  };

  return (
    <AppShell title="Graph View" subtitle="Interactive identity graph — click nodes and edges to inspect">
      <div className="grid grid-cols-1 xl:grid-cols-[1fr_360px] gap-4">
        {/* Graph area */}
        <Card className="glass border-border/60 overflow-hidden">
          <div className="flex items-center gap-2 p-3 border-b border-border/60 flex-wrap">
            {/* Investigation selector */}
            <AsyncBoundary resource={invRes}>
              {(investigations) => (
                <Select
                  value={selectedInvId ?? "__none__"}
                  onValueChange={handleInvChange}
                >
                  <SelectTrigger className="w-[200px] h-8 bg-surface/60 text-xs" aria-label="Select investigation">
                    <Network className="h-3.5 w-3.5 mr-1.5 text-muted-foreground" />
                    <SelectValue placeholder="Select investigation…" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__none__">— Sample graph —</SelectItem>
                    {investigations.map((inv) => (
                      <SelectItem key={inv.id} value={inv.id}>
                        {inv.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            </AsyncBoundary>

            {/* Search */}
            <div className="relative flex-1 min-w-[160px]">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />
              <label htmlFor="graph-search" className="sr-only">Find in graph</label>
              <Input
                id="graph-search"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Find node…"
                className="h-8 pl-8 bg-surface/60 text-xs"
              />
            </div>

            <Button variant="ghost" size="sm" className="gap-1 h-8">
              <Layers className="h-3.5 w-3.5" aria-hidden="true" /> Layout
            </Button>

            {/* Zoom controls */}
            <div className="ml-auto flex items-center gap-1">
              <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setZoom((z) => Math.max(40, z - 10))} aria-label="Zoom out">
                <ZoomOut className="h-3.5 w-3.5" aria-hidden="true" />
              </Button>
              <span className="text-xs font-mono w-10 text-center text-muted-foreground">{zoom}%</span>
              <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setZoom((z) => Math.min(200, z + 10))} aria-label="Zoom in">
                <ZoomIn className="h-3.5 w-3.5" aria-hidden="true" />
              </Button>
              <Button variant="ghost" size="icon" className="h-8 w-8" aria-label="Fit to screen" onClick={fitToScreen}>
                <Maximize2 className="h-3.5 w-3.5" aria-hidden="true" />
              </Button>
            </div>
          </div>

          <div className="relative grid-bg h-[620px] overflow-hidden">
            <AsyncBoundary resource={resource}>
              {(data) => {
                if (data.nodes.length === 0) {
                  return (
                    <div className="absolute inset-0 flex items-center justify-center">
                      <EmptyState
                        title="No identifiers found"
                        description="Run connectors on this investigation to populate the graph."
                      />
                    </div>
                  );
                }

                const current: Selection =
                  selection.node || selection.edge
                    ? selection
                    : { node: data.nodes[0] ?? null, edge: null };

                return (
                  <>
                    <GraphCanvas
                      data={data}
                      zoom={zoom}
                      pan={pan}
                      positions={positions}
                      selection={current}
                      query={query}
                      onSelect={setSelection}
                      onNodeDrag={handleNodeDrag}
                    />
                    <GraphLegend />
                  </>
                );
              }}
            </AsyncBoundary>
          </div>
        </Card>

        {/* Side panel */}
        <div className="space-y-4">
          <Card className="glass p-5 border-border/60">
            <AsyncBoundary resource={resource}>
              {(data) => {
                const current: Selection =
                  selection.node || selection.edge
                    ? selection
                    : { node: data.nodes[0] ?? null, edge: null };
                return (
                  <>
                    <div className="flex items-center justify-between">
                      <h3 className="font-display font-semibold">
                        {current.edge ? "Edge Details" : "Node Details"}
                      </h3>
                      {current.node?.primary && (
                        <span className="text-[10px] uppercase tracking-widest text-primary">Seed</span>
                      )}
                    </div>
                    {current.node && !current.edge && (
                      <NodeDetails node={current.node} edges={data.edges} nodes={data.nodes} />
                    )}
                    {current.edge && <EdgeDetails edge={current.edge} nodes={data.nodes} />}
                    {!current.node && !current.edge && (
                      <p className="mt-4 text-sm text-muted-foreground">Click a node or edge to inspect it.</p>
                    )}
                  </>
                );
              }}
            </AsyncBoundary>
          </Card>

          <Card className="glass p-5 border-border/60">
            <h3 className="font-display font-semibold">Graph Metrics</h3>
            <AsyncBoundary resource={resource}>
              {(data) => (
                <div className="mt-3 grid grid-cols-3 gap-3 text-center">
                  {[
                    ["Nodes", data.nodes.length],
                    ["Edges", data.edges.length],
                    ["Types", new Set(data.nodes.map((n) => n.type)).size],
                  ].map(([l, v]) => (
                    <div key={l as string}>
                      <div className="text-xl font-display font-bold text-primary">{v}</div>
                      <div className="text-[10px] uppercase tracking-widest text-muted-foreground">{l}</div>
                    </div>
                  ))}
                </div>
              )}
            </AsyncBoundary>
          </Card>

          {/* Search results */}
          {query && (
            <Card className="glass p-5 border-border/60">
              <h3 className="font-display font-semibold text-sm">Search Results</h3>
              <AsyncBoundary resource={resource}>
                {(data) => {
                  const matches = data.nodes.filter((n) =>
                    n.label.toLowerCase().includes(query.toLowerCase())
                  );
                  if (matches.length === 0) {
                    return <p className="mt-2 text-xs text-muted-foreground">No nodes match "{query}"</p>;
                  }
                  return (
                    <div className="mt-2 space-y-1">
                      {matches.map((n) => {
                        const Icon = iconMap[n.type];
                        return (
                          <button
                            key={n.id}
                            className="w-full flex items-center gap-2 p-2 rounded-lg hover:bg-white/5 text-xs"
                            onClick={() => setSelection({ node: n, edge: null })}
                          >
                            <span className={cn("h-5 w-5 rounded-full grid place-items-center shrink-0", colorMap[n.type])}>
                              <Icon className="h-3 w-3" />
                            </span>
                            <span className="truncate font-mono">{n.label}</span>
                            <span className="ml-auto text-muted-foreground capitalize">{n.type}</span>
                          </button>
                        );
                      })}
                    </div>
                  );
                }}
              </AsyncBoundary>
            </Card>
          )}
        </div>
      </div>
    </AppShell>
  );
}
