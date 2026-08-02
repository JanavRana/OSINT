import { createFileRoute } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { SeverityBadge } from "@/components/badges";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  Mail, Globe, Share2, Wallet, Server, Settings2, Search, Calendar, Clock,
} from "lucide-react";
import { AsyncBoundary, EmptyState } from "@/components/states";
import { useInvestigations, useTimeline } from "@/hooks/use-osint-data";
import { fmtDate } from "@/lib/format";
import type { TimelineChannel, TimelineEvent } from "@/types/domain";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/timeline")({
  head: () => ({ meta: [{ title: "Timeline — AXIOM OSINT" }] }),
  component: Timeline,
});

type ChannelFilter = "all" | TimelineChannel;

const channelIcon: Record<TimelineChannel, typeof Mail> = {
  email: Mail,
  domain: Globe,
  social: Share2,
  wallet: Wallet,
  network: Server,
  system: Settings2,
};

const channelColor: Record<TimelineChannel, string> = {
  email: "text-primary bg-primary/15",
  domain: "text-accent bg-accent/15",
  social: "text-warning bg-warning/15",
  wallet: "text-success bg-success/15",
  network: "text-destructive bg-destructive/15",
  system: "text-muted-foreground bg-white/5",
};

// ─── Event card ───────────────────────────────────────────────────────────────

function TimelineEventCard({ event }: { event: TimelineEvent }) {
  const Icon = channelIcon[event.channel];
  return (
    <div className="relative pl-14">
      <div
        className={cn(
          "absolute left-6 -translate-x-1/2 top-4 h-4 w-4 rounded-full grid place-items-center",
          channelColor[event.channel]
        )}
        aria-hidden="true"
      >
        <Icon className="h-2.5 w-2.5" />
      </div>
      <Card className="glass p-4 border-border/60">
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="font-medium text-foreground">{event.actor}</span>
          <span className="text-muted-foreground">{event.action}</span>
          <span className="font-mono">{event.target}</span>
          <SeverityBadge severity={event.severity} />
          <time dateTime={event.time} className="ml-auto text-muted-foreground flex items-center gap-1">
            <Clock className="h-3 w-3" aria-hidden="true" />
            {fmtDate(event.time)}
          </time>
        </div>
        <div className="mt-2 text-sm text-muted-foreground">{event.details}</div>
      </Card>
    </div>
  );
}

// ─── Date group header ────────────────────────────────────────────────────────

function DateGroupHeader({ date }: { date: string }) {
  return (
    <div className="pl-14 flex items-center gap-3 my-4">
      <div className="absolute left-6 -translate-x-1/2 h-6 w-6 rounded-full bg-surface border border-border/60 grid place-items-center">
        <Calendar className="h-3 w-3 text-muted-foreground" />
      </div>
      <div className="text-[11px] uppercase tracking-widest font-medium text-muted-foreground bg-surface/80 backdrop-blur-sm px-3 py-1 rounded-full border border-border/60">
        {date}
      </div>
    </div>
  );
}

// ─── Group events by date ─────────────────────────────────────────────────────

function groupByDate(events: TimelineEvent[]): Array<{ date: string; events: TimelineEvent[] }> {
  const groups = new Map<string, TimelineEvent[]>();
  for (const e of events) {
    const d = new Date(e.time).toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
    const arr = groups.get(d) ?? [];
    arr.push(e);
    groups.set(d, arr);
  }
  return Array.from(groups.entries()).map(([date, evts]) => ({ date, events: evts }));
}

// ─── Timeline page ────────────────────────────────────────────────────────────

function Timeline() {
  const [q, setQ] = useState("");
  const [ch, setCh] = useState<ChannelFilter>("all");
  const [selectedInvId, setSelectedInvId] = useState<string | undefined>(undefined);

  const invRes = useInvestigations();
  const resource = useTimeline(selectedInvId);

  const filtered = useMemo(
    () =>
      (resource.data ?? []).filter(
        (e) =>
          (ch === "all" || e.channel === ch) &&
          (q === "" ||
            (e.actor + e.target + e.details).toLowerCase().includes(q.toLowerCase()))
      ),
    [resource.data, q, ch]
  );

  const grouped = useMemo(() => groupByDate(filtered), [filtered]);

  const handleInvChange = (val: string) => {
    setSelectedInvId(val === "__none__" ? undefined : val);
    setQ("");
  };

  return (
    <AppShell title="Timeline" subtitle="Chronological event log across all connectors">
      <Card className="glass p-4 border-border/60">
        <div className="flex flex-wrap items-center gap-3">
          {/* Investigation selector */}
          <AsyncBoundary resource={invRes}>
            {(investigations) => (
              <Select
                value={selectedInvId ?? "__none__"}
                onValueChange={handleInvChange}
              >
                <SelectTrigger className="w-[220px] bg-surface/60" aria-label="Select investigation">
                  <SelectValue placeholder="Select investigation…" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__none__">All investigations</SelectItem>
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
          <div className="relative flex-1 min-w-[220px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" aria-hidden="true" />
            <label htmlFor="timeline-search" className="sr-only">Search events</label>
            <Input
              id="timeline-search"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search events…"
              className="pl-9 bg-surface/60"
            />
          </div>

          {/* Channel filter */}
          <Select value={ch} onValueChange={(v) => setCh(v as ChannelFilter)}>
            <SelectTrigger className="w-[160px] bg-surface/60" aria-label="Channel filter">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All channels</SelectItem>
              <SelectItem value="email">Email</SelectItem>
              <SelectItem value="domain">Domain</SelectItem>
              <SelectItem value="social">Social</SelectItem>
              <SelectItem value="wallet">Wallet</SelectItem>
              <SelectItem value="network">Network</SelectItem>
              <SelectItem value="system">System</SelectItem>
            </SelectContent>
          </Select>

          {/* Event count */}
          {resource.data && (
            <span className="text-xs text-muted-foreground ml-auto">
              {filtered.length} event{filtered.length !== 1 ? "s" : ""}
            </span>
          )}
        </div>
      </Card>

      <div className="mt-6 relative">
        {/* Vertical timeline line */}
        <div
          className="absolute left-6 top-0 bottom-0 w-px bg-gradient-to-b from-primary/40 via-border to-transparent"
          aria-hidden="true"
        />

        <AsyncBoundary resource={resource}>
          {() => (
            <div>
              {!selectedInvId && filtered.length === 0 ? (
                <EmptyState
                  title="Select an investigation"
                  description="Choose an investigation from the dropdown to see its timeline events."
                  icon={<Calendar className="h-5 w-5" />}
                />
              ) : filtered.length === 0 ? (
                <EmptyState
                  title="No events match your filters."
                  description="Try broadening the search or channel selection, or run an investigation to generate events."
                />
              ) : (
                <div>
                  {grouped.map(({ date, events }) => (
                    <div key={date} className="relative">
                      <DateGroupHeader date={date} />
                      <div className="space-y-3">
                        {events.map((e) => (
                          <TimelineEventCard key={e.id} event={e} />
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </AsyncBoundary>
      </div>
    </AppShell>
  );
}
