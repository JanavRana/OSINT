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
  email: "text-primary bg-primary/10 border-primary/40",
  domain: "text-accent bg-accent/10 border-accent/40",
  user: "text-warning bg-warning/10 border-warning/40",
  wallet: "text-success bg-success/10 border-success/40",
  ip: "text-destructive bg-destructive/10 border-destructive/40",
};

interface Selection {
  node: GraphNode | null;
  edge: GraphEdge | null;
}

type NodePositions = Map<string, { x: number; y: number }>;

// ─── Draggable + Pannable Graph Canvas ───────────────────────────────────────

function GraphCanvas({
  data,
  zoom,
  pan,
  positions,
  selection,
  query,
  onSelect,
  onNodeDrag,
  onPanChange,
  onZoomChange,
}: {
  data: GraphData;
  zoom: number;
  pan: { x: number; y: number };
  positions: NodePositions;
  selection: Selection;
  query: string;
  onSelect: (s: Selection) => void;
  onNodeDrag: (id: string, x: number, y: number) => void;
  onPanChange: (pan: { x: number; y: number }) => void;
  onZoomChange: (zoom: number) => void;
}) {
  const { nodes, edges } = data;
  const containerRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  const dragState = useRef<{
    type: "node" | "pan";
    nodeId?: string;
    startX: number;
    startY: number;
    origX: number;
    origY: number;
  } | null>(null);

  const getPos = (n: GraphNode) => positions.get(n.id) ?? { x: n.x, y: n.y };

  const lowerQ = query.toLowerCase();
  const matchingIds = useMemo(() => {
    if (!lowerQ) return new Set<string>();
    return new Set(nodes.filter((n) => n.label.toLowerCase().includes(lowerQ)).map((n) => n.id));
  }, [nodes, lowerQ]);

  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    const delta = -e.deltaY * 0.05;
    onZoomChange(Math.max(30, Math.min(250, zoom + delta)));
  }, [zoom, onZoomChange]);

  const handleNodeMouseDown = useCallback((
    e: React.MouseEvent,
    nodeId: string,
    currentX: number,
    currentY: number,
  ) => {
    e.preventDefault();
    e.stopPropagation();
    const scale = zoom / 100;

    dragState.current = {
      type: "node",
      nodeId,
      startX: e.clientX,
      startY: e.clientY,
      origX: currentX,
      origY: currentY,
    };

    const onMove = (me: MouseEvent) => {
      if (!dragState.current || dragState.current.type !== "node") return;
      const container = containerRef.current;
      if (!container) return;
      const rect = container.getBoundingClientRect();
      const pxPerPercW = (rect.width * scale) / 100;
      const pxPerPercH = (rect.height * scale) / 100;
      const dx = (me.clientX - dragState.current.startX) / pxPerPercW;
      const dy = (me.clientY - dragState.current.startY) / pxPerPercH;
      onNodeDrag(dragState.current.nodeId!, dragState.current.origX + dx, dragState.current.origY + dy);
    };
    const onUp = () => {
      dragState.current = null;
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
  }, [zoom, onNodeDrag]);

  const handleCanvasMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.button !== 0) return;
    dragState.current = {
      type: "pan",
      startX: e.clientX,
      startY: e.clientY,
      origX: pan.x,
      origY: pan.y,
    };

    const onMove = (me: MouseEvent) => {
      if (!dragState.current || dragState.current.type !== "pan") return;
      const dx = me.clientX - dragState.current.startX;
      const dy = me.clientY - dragState.current.startY;
      onPanChange({ x: dragState.current.origX + dx, y: dragState.current.origY + dy });
    };
    const onUp = () => {
      dragState.current = null;
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
  }, [pan, onPanChange]);

  const renderEdges = () => (
    <svg
      ref={svgRef}
      viewBox="0 0 100 100"
      preserveAspectRatio="none"
      className="absolute inset-0 h-full w-full pointer-events-none"
      aria-hidden="true"
    >
      <defs>
        <marker id="arrowhead" markerWidth="3" markerHeight="2" refX="2.8" refY="1" orient="auto" markerUnits="strokeWidth">
          <polygon points="0 0, 3 1, 0 2" fill="oklch(0.72 0.14 220)" opacity="0.8" />
        </marker>
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

        const x1 = posA.x;
        const y1 = posA.y;
        const x2 = posB.x;
        const y2 = posB.y;
        const mx = (x1 + x2) / 2;
        const my = (y1 + y2) / 2;
        const len = Math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2) || 1;
        const ox = -(y2 - y1) / len * 6;
        const oy = (x2 - x1) / len * 6;
        const d = `M ${x1} ${y1} Q ${mx + ox} ${my + oy} ${x2} ${y2}`;

        return (
          <path
            key={i}
            d={d}
            fill="none"
            stroke={active || highlighted ? "oklch(0.72 0.14 220)" : "oklch(0.30 0.015 255)"}
            strokeWidth={active || highlighted ? 0.35 : 0.2}
            strokeDasharray={active ? "0" : "2 2"}
            opacity={lowerQ && !matchingIds.has(e.from) && !matchingIds.has(e.to) ? 0.15 : 0.7}
            markerEnd="url(#arrowhead)"
            className="pointer-events-auto cursor-pointer transition-opacity"
            onClick={() => onSelect({ node: null, edge: e })}
          />
        );
      })}
    </svg>
  );

  return (
    <div
      ref={containerRef}
      className="absolute inset-0 overflow-hidden cursor-grab active:cursor-grabbing select-none"
      onMouseDown={handleCanvasMouseDown}
      onWheel={handleWheel}
      style={{ userSelect: "none" }}
    >
      <div
        className="absolute inset-0"
        style={{
          transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom / 100})`,
          transformOrigin: "center center",
        }}
      >
        {renderEdges()}

        {nodes.map((n) => {
          const Icon = iconMap[n.type];
          const size = n.size ?? 26;
          const isSel = selection.node?.id === n.id;
          const isMatch = lowerQ ? matchingIds.has(n.id) : true;
          const pos = getPos(n);

          const displayLabel = n.type === "user" && n.platformDisplayName 
            ? n.platformDisplayName 
            : n.label;

          return (
            <button
              key={n.id}
              className={cn(
                "absolute -translate-x-1/2 -translate-y-1/2 group focus-visible:outline-none transition-opacity",
                !isMatch && lowerQ && "opacity-20"
              )}
              style={{ left: `${pos.x}%`, top: `${pos.y}%` }}
              aria-label={`${n.type} ${displayLabel}`}
              aria-pressed={isSel}
              onMouseDown={(e) => handleNodeMouseDown(e, n.id, pos.x, pos.y)}
              onClick={(e) => { e.stopPropagation(); onSelect({ node: n, edge: null }); }}
            >
              <div
                className={cn(
                  "relative rounded-full border grid place-items-center transition-all bg-surface",
                  colorMap[n.type],
                  isSel && "ring-2 ring-primary ring-offset-1 ring-offset-background scale-110",
                )}
                style={{ height: size, width: size }}
                aria-hidden="true"
              >
                <Icon className="h-3.5 w-3.5" />
              </div>
              <div className="mt-1 text-[10px] font-mono text-muted-foreground whitespace-nowrap text-center opacity-90 group-hover:opacity-100 max-w-[130px] truncate bg-surface/80 px-1 rounded border border-border/40">
                {displayLabel}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ─── Legend ───────────────────────────────────────────────────────────────────

function GraphLegend() {
  return (
    <div className="absolute bottom-2.5 left-2.5 bg-surface/90 border border-border rounded-sm p-2 text-xs font-mono pointer-events-none">
      <div className="text-[10px] uppercase font-bold text-muted-foreground mb-1.5">Entity Types</div>
      <div className="grid grid-cols-2 gap-x-3 gap-y-1">
        {(Object.keys(iconMap) as GraphNodeType[]).map((t) => {
          const Icon = iconMap[t];
          return (
            <div key={t} className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
              <span className={cn("h-3.5 w-3.5 rounded-full grid place-items-center border", colorMap[t])} aria-hidden="true">
                <Icon className="h-2 w-2" />
              </span>
              <span className="capitalize">{t}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── Node / Edge detail panels ────────────────────────────────────────────────

function NodeDetails({ node, edges, nodes }: { node: GraphNode; edges: GraphEdge[]; nodes: GraphNode[] }) {
  const Icon = iconMap[node.type];
  const connected = edges.filter((e) => e.from === node.id || e.to === node.id);
  return (
    <div className="mt-3 space-y-3 font-mono text-xs">
      <div className="flex items-center gap-2.5 p-2 rounded-sm bg-surface-2 border border-border">
        <div className={cn("h-9 w-9 rounded-sm border grid place-items-center shrink-0", colorMap[node.type])} aria-hidden="true">
          <Icon className="h-4 w-4" />
        </div>
        <div className="min-w-0">
          <div className="text-[9px] uppercase tracking-widest text-muted-foreground">{node.type}</div>
          <div className="font-mono text-xs font-bold text-foreground truncate max-w-[200px]">{node.label}</div>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-2 text-xs">
        <Field label="Connections" value={String(connected.length)} mono />
        <Field label="Seed Entity" value={node.primary ? "YES" : "NO"} mono />
      </div>
      {connected.length > 0 && (
        <div>
          <div className="text-[9px] uppercase tracking-widest font-mono text-muted-foreground mb-1.5">Connected Relations</div>
          <div className="space-y-1 max-h-40 overflow-y-auto">
            {connected.map((e, i) => {
              const otherId = e.from === node.id ? e.to : e.from;
              const other = nodes.find((n) => n.id === otherId);
              return (
                <div key={i} className="text-[11px] font-mono flex items-center gap-1.5 p-1.5 rounded-sm bg-surface-2/60 border border-border/40">
                  <span className="h-1.5 w-1.5 rounded-full bg-primary shrink-0" aria-hidden="true" />
                  <span className="text-muted-foreground">{e.kind}</span>
                  <span className="ml-auto font-mono text-[10px] text-foreground truncate max-w-[110px]">{other?.label ?? otherId}</span>
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
    <div className="mt-3 space-y-2 text-xs font-mono">
      <Field label="Relation Kind" value={edge.kind} mono />
      <Field label="Source (From)" value={nodes.find((n) => n.id === edge.from)?.label ?? edge.from} mono />
      <Field label="Target (To)" value={nodes.find((n) => n.id === edge.to)?.label ?? edge.to} mono />
    </div>
  );
}

// ─── Main Graph page ──────────────────────────────────────────────────────────

function Graph() {
  const invRes = useInvestigations();
  const [selectedInvId, setSelectedInvId] = useState<string | undefined>(undefined);
  const resource = useGraph(selectedInvId);
  const [zoom, setZoom] = useState(100);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [selection, setSelection] = useState<Selection>({ node: null, edge: null });
  const [query, setQuery] = useState("");
  const [positions, setPositions] = useState<NodePositions>(new Map());

  const handleNodeDrag = useCallback((id: string, x: number, y: number) => {
    setPositions((prev) => {
      const next = new Map(prev);
      next.set(id, { x: Math.max(3, Math.min(97, x)), y: Math.max(3, Math.min(97, y)) });
      return next;
    });
  }, []);

  const handleZoomChange = useCallback((newZoom: number) => {
    setZoom(Math.round(Math.max(30, Math.min(250, newZoom))));
  }, []);

  const handleInvChange = (invId: string) => {
    setSelectedInvId(invId === "__none__" ? undefined : invId);
    setPositions(new Map());
    setSelection({ node: null, edge: null });
    setQuery("");
    setPan({ x: 0, y: 0 });
    setZoom(100);
  };

  const fitToScreen = () => {
    setZoom(100);
    setPan({ x: 0, y: 0 });
    setPositions(new Map());
  };

  return (
    <AppShell title="Identity Graph Canvas" subtitle="Interactive entity relationship visualizer · Scroll to zoom, drag canvas to pan, drag nodes to reposition">
      <div className="grid grid-cols-1 xl:grid-cols-[1fr_340px] gap-3">
        {/* Graph area */}
        <Card className="border-border bg-surface rounded-md overflow-hidden">
          <div className="flex items-center gap-2 p-2.5 border-b border-border bg-surface-2/40 flex-wrap">
            {/* Investigation selector */}
            <AsyncBoundary resource={invRes}>
              {(investigations) => (
                <Select
                  value={selectedInvId ?? "__none__"}
                  onValueChange={handleInvChange}
                >
                  <SelectTrigger className="w-[190px] h-8 bg-surface-2 text-xs font-mono border-border" aria-label="Select investigation">
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
            <div className="relative flex-1 min-w-[150px]">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />
              <label htmlFor="graph-search" className="sr-only">Find in graph</label>
              <Input
                id="graph-search"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search node label..."
                className="h-8 pl-8 bg-surface-2 text-xs font-mono border-border"
              />
            </div>

            <Button variant="ghost" size="sm" className="gap-1 h-8 text-xs font-mono" onClick={fitToScreen}>
              <Layers className="h-3.5 w-3.5" aria-hidden="true" /> FIT
            </Button>

            {/* Zoom controls */}
            <div className="ml-auto flex items-center gap-1">
              <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => handleZoomChange(zoom - 15)} aria-label="Zoom out">
                <ZoomOut className="h-3.5 w-3.5" aria-hidden="true" />
              </Button>
              <span className="text-xs font-mono w-10 text-center text-muted-foreground">{Math.round(zoom)}%</span>
              <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => handleZoomChange(zoom + 15)} aria-label="Zoom in">
                <ZoomIn className="h-3.5 w-3.5" aria-hidden="true" />
              </Button>
              <Button variant="ghost" size="icon" className="h-8 w-8" aria-label="Fit to screen" onClick={fitToScreen}>
                <Maximize2 className="h-3.5 w-3.5" aria-hidden="true" />
              </Button>
            </div>
          </div>

          <div className="relative grid-bg h-[600px] overflow-hidden">
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
                      onPanChange={setPan}
                      onZoomChange={handleZoomChange}
                    />
                    <GraphLegend />
                  </>
                );
              }}
            </AsyncBoundary>
          </div>
        </Card>

        {/* Side panel */}
        <div className="space-y-3">
          <Card className="p-4 border-border bg-surface rounded-md">
            <AsyncBoundary resource={resource}>
              {(data) => {
                const current: Selection =
                  selection.node || selection.edge
                    ? selection
                    : { node: data.nodes[0] ?? null, edge: null };
                return (
                  <>
                    <div className="flex items-center justify-between pb-2 border-b border-border/60">
                      <h3 className="font-display text-xs font-bold uppercase tracking-wider text-foreground">
                        {current.edge ? "Edge Inspector" : "Node Inspector"}
                      </h3>
                      {current.node?.primary && (
                        <span className="text-[9px] font-mono font-bold uppercase tracking-widest text-primary bg-primary/10 border border-primary/30 px-1.5 py-0.5 rounded-sm">SEED</span>
                      )}
                    </div>
                    {current.node && !current.edge && (
                      <NodeDetails node={current.node} edges={data.edges} nodes={data.nodes} />
                    )}
                    {current.edge && <EdgeDetails edge={current.edge} nodes={data.nodes} />}
                    {!current.node && !current.edge && (
                      <p className="mt-3 text-xs font-mono text-muted-foreground">Click a node or edge to inspect it.</p>
                    )}
                  </>
                );
              }}
            </AsyncBoundary>
          </Card>

          <Card className="p-4 border-border bg-surface rounded-md">
            <h3 className="font-display text-xs font-bold uppercase tracking-wider text-foreground pb-2 border-b border-border/60">Topology Metrics</h3>
            <AsyncBoundary resource={resource}>
              {(data) => (
                <div className="mt-3 grid grid-cols-3 gap-2 text-center font-mono">
                  {[
                    ["NODES", data.nodes.length],
                    ["EDGES", data.edges.length],
                    ["TYPES", new Set(data.nodes.map((n) => n.type)).size],
                  ].map(([l, v]) => (
                    <div key={l as string} className="p-2 rounded-sm bg-surface-2 border border-border">
                      <div className="text-base font-bold text-primary">{v}</div>
                      <div className="text-[9px] uppercase tracking-widest text-muted-foreground mt-0.5">{l}</div>
                    </div>
                  ))}
                </div>
              )}
            </AsyncBoundary>
          </Card>

          {/* Search results */}
          {query && (
            <Card className="p-4 border-border bg-surface rounded-md">
              <h3 className="font-display text-xs font-bold uppercase tracking-wider text-foreground pb-2 border-b border-border/60">Query Results</h3>
              <AsyncBoundary resource={resource}>
                {(data) => {
                  const matches = data.nodes.filter((n) =>
                    n.label.toLowerCase().includes(query.toLowerCase())
                  );
                  if (matches.length === 0) {
                    return <p className="mt-2 text-xs font-mono text-muted-foreground">No nodes match "{query}"</p>;
                  }
                  return (
                    <div className="mt-2 space-y-1">
                      {matches.map((n) => {
                        const Icon = iconMap[n.type];
                        return (
                          <button
                            key={n.id}
                            className="w-full flex items-center gap-2 p-1.5 rounded-sm hover:bg-surface-2 text-xs font-mono border border-border/40"
                            onClick={() => setSelection({ node: n, edge: null })}
                          >
                            <span className={cn("h-4 w-4 rounded-full grid place-items-center shrink-0 border", colorMap[n.type])}>
                              <Icon className="h-2.5 w-2.5" />
                            </span>
                            <span className="truncate text-foreground">{n.label}</span>
                            <span className="ml-auto text-[10px] text-muted-foreground uppercase">{n.type}</span>
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

