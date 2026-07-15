import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { AppShell } from "@/components/app-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Mail, Globe, User, Wallet, Server, ZoomIn, ZoomOut, Maximize2,
  Filter, Search, Layers, Play,
} from "lucide-react";
import { AsyncBoundary } from "@/components/states";
import { Field } from "@/components/field";
import { useGraph } from "@/hooks/use-osint-data";
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

function GraphCanvas({
  data,
  zoom,
  selection,
  onSelect,
}: {
  data: GraphData;
  zoom: number;
  selection: Selection;
  onSelect: (s: Selection) => void;
}) {
  const { nodes, edges } = data;
  return (
    <div className="absolute inset-0 origin-center transition-transform" style={{ transform: `scale(${zoom})` }}>
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
          const active = selection.edge === e;
          return (
            <line
              key={i}
              x1={`${a.x}%`} y1={`${a.y}%`} x2={`${b.x}%`} y2={`${b.y}%`}
              stroke={active ? "oklch(0.82 0.17 195)" : "url(#edge-grad)"}
              strokeWidth={active ? 2 : 1}
              strokeDasharray={active ? "0" : "4 4"}
              className="pointer-events-auto cursor-pointer"
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
        return (
          <button
            key={n.id}
            onClick={() => onSelect({ node: n, edge: null })}
            className="absolute -translate-x-1/2 -translate-y-1/2 group focus-visible:outline-none"
            style={{ left: `${n.x}%`, top: `${n.y}%` }}
            aria-label={`${n.type} ${n.label}`}
            aria-pressed={isSel}
          >
            {n.primary && <div className="absolute inset-0 -m-3 rounded-full bg-primary/30 blur-xl" aria-hidden="true" />}
            <div
              className={cn(
                "relative rounded-full border grid place-items-center transition-all",
                colorMap[n.type],
                isSel && "ring-2 ring-primary ring-offset-2 ring-offset-background",
                n.primary && "shadow-[0_0_30px_-4px_var(--primary)]",
              )}
              style={{ height: size, width: size }}
              aria-hidden="true"
            >
              <Icon className="h-3.5 w-3.5" />
            </div>
            <div className="mt-1 text-[10px] font-mono text-muted-foreground whitespace-nowrap text-center opacity-80 group-hover:opacity-100">
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

function NodeDetails({
  node,
  edges,
  nodes,
}: {
  node: GraphNode;
  edges: GraphEdge[];
  nodes: GraphNode[];
}) {
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
          <div className="font-mono text-sm truncate">{node.label}</div>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3 text-xs">
        <Field label="Confidence" value="92%" />
        <Field label="Sources" value="6" />
        <Field label="First seen" value="2024-11-02" />
        <Field label="Last seen" value="2 hrs ago" />
      </div>
      <div>
        <div className="text-[10px] uppercase tracking-widest text-muted-foreground mb-2">Connected</div>
        <div className="space-y-1">
          {connected.map((e, i) => (
            <div key={i} className="text-xs flex items-center gap-2 p-2 rounded-md bg-white/[0.03]">
              <span className="h-1.5 w-1.5 rounded-full bg-primary" aria-hidden="true" />
              <span className="text-muted-foreground">{e.kind}</span>
              <span className="ml-auto font-mono text-[10px]">
                {nodes.find((n) => n.id === (e.from === node.id ? e.to : e.from))?.label}
              </span>
            </div>
          ))}
        </div>
      </div>
      <Button className="w-full gap-2 bg-gradient-to-r from-primary to-accent text-primary-foreground">
        <Play className="h-3.5 w-3.5" aria-hidden="true" /> Expand from node
      </Button>
    </div>
  );
}

function EdgeDetails({ edge, nodes }: { edge: GraphEdge; nodes: GraphNode[] }) {
  return (
    <div className="mt-4 space-y-3 text-sm">
      <Field label="Relation" value={edge.kind} />
      <Field label="From" value={nodes.find((n) => n.id === edge.from)?.label ?? ""} mono />
      <Field label="To" value={nodes.find((n) => n.id === edge.to)?.label ?? ""} mono />
      <Field label="Weight" value="0.82" />
      <Field label="Discovered by" value="Whoxy + Telegram Scraper" />
    </div>
  );
}

function Graph() {
  const resource = useGraph();
  const [zoom, setZoom] = useState(1);
  const [selection, setSelection] = useState<Selection>({ node: null, edge: null });

  return (
    <AppShell title="Graph View" subtitle="Interactive identity graph — click nodes and edges to inspect">
      <div className="grid grid-cols-1 xl:grid-cols-[1fr_360px] gap-4">
        {/* Graph area */}
        <Card className="glass border-border/60 overflow-hidden">
          <div className="flex items-center gap-2 p-3 border-b border-border/60">
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />
              <label htmlFor="graph-search" className="sr-only">Find in graph</label>
              <Input id="graph-search" placeholder="Find in graph…" className="h-8 pl-8 bg-surface/60 text-xs" />
            </div>
            <Button variant="ghost" size="sm" className="gap-1 h-8">
              <Filter className="h-3.5 w-3.5" aria-hidden="true" /> Filter
            </Button>
            <Button variant="ghost" size="sm" className="gap-1 h-8">
              <Layers className="h-3.5 w-3.5" aria-hidden="true" /> Layout
            </Button>
            <div className="ml-auto flex items-center gap-1">
              <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setZoom((z) => Math.max(0.5, z - 0.1))} aria-label="Zoom out">
                <ZoomOut className="h-3.5 w-3.5" aria-hidden="true" />
              </Button>
              <span className="text-xs font-mono w-10 text-center text-muted-foreground">{Math.round(zoom * 100)}%</span>
              <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setZoom((z) => Math.min(2, z + 0.1))} aria-label="Zoom in">
                <ZoomIn className="h-3.5 w-3.5" aria-hidden="true" />
              </Button>
              <Button variant="ghost" size="icon" className="h-8 w-8" aria-label="Fit to screen">
                <Maximize2 className="h-3.5 w-3.5" aria-hidden="true" />
              </Button>
            </div>
          </div>

          <div className="relative grid-bg h-[620px] overflow-hidden">
            <AsyncBoundary resource={resource}>
              {(data) => {
                // Default selection to seed node on first hydrate.
                const current: Selection =
                  selection.node || selection.edge
                    ? selection
                    : { node: data.nodes[0] ?? null, edge: null };
                return (
                  <>
                    <GraphCanvas
                      data={data}
                      zoom={zoom}
                      selection={current}
                      onSelect={setSelection}
                    />
                    <GraphLegend />
                    <GraphSidePanelPortal
                      selection={current}
                      data={data}
                    />
                  </>
                );
              }}
            </AsyncBoundary>
          </div>
        </Card>

        {/* Side panel (mounted via portal-like sibling below the graph) */}
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
                    ["Clusters", 3],
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
        </div>
      </div>
    </AppShell>
  );
}

// Kept as no-op sibling to preserve original layout tree; details render in
// the side panel above. Intentionally renders nothing.
function GraphSidePanelPortal(_props: { selection: Selection; data: GraphData }) {
  return null;
}
