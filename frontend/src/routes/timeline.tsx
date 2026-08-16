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
  email: "text-primary bg-primary/10 border-primary/30",
  domain: "text-accent bg-accent/10 border-accent/30",
  social: "text-warning bg-warning/10 border-warning/30",
  wallet: "text-success bg-success/10 border-success/30",
  network: "text-destructive bg-destructive/10 border-destructive/30",
  system: "text-muted-foreground bg-surface-2 border-border",
};

// ─── Event card ───────────────────────────────────────────────────────────────

function TimelineEventCard({ event }: { event: TimelineEvent }) {
  const Icon = channelIcon[event.channel];
  return (
    <div className="relative pl-10">
      <div
        className={cn(
          "absolute left-3 -translate-x-1/2 top-3 h-5 w-5 rounded-sm border grid place-items-center bg-surface shrink-0 z-10",
          channelColor[event.channel]
        )}
        aria-hidden="true"
      >
        <Icon className="h-3 w-3" />
      </div>
      <Card className="p-3 border-border bg-surface rounded-md font-mono text-xs">
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="font-bold text-foreground font-sans">{event.actor}</span>
          <span className="text-muted-foreground uppercase text-[10px]">{event.action}</span>
          <span className="text-primary font-bold">{event.target}</span>
          <SeverityBadge severity={event.severity} />
          <time dateTime={event.time} className="ml-auto text-[11px] text-muted-foreground flex items-center gap-1">
            <Clock className="h-3 w-3" aria-hidden="true" />
            {fmtDate(event.time)}
          </time>
        </div>
        <div className="mt-1.5 text-xs text-muted-foreground font-sans">{event.details}</div>
      </Card>
    </div>
  );
}

// ─── Date group header ────────────────────────────────────────────────────────

function DateGroupHeader({ date }: { date: string }) {
  return (
    <div className="pl-10 flex items-center gap-2 my-3">
      <div className="absolute left-3 -translate-x-1/2 h-5 w-5 rounded-sm bg-surface-2 border border-border grid place-items-center">
        <Calendar className="h-3 w-3 text-muted-foreground" />
      </div>
      <div className="text-[10px] uppercase font-mono tracking-widest font-bold text-muted-foreground bg-surface-2 px-2.5 py-0.5 rounded-sm border border-border">
        {date}
      </div>
    </div>
  );
}

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
    <AppShell title="Event Telemetry Log" subtitle="Chronological intelligence event stream across all executed connectors">
      <Card className="p-3 border-border bg-surface rounded-md">
        <div className="flex flex-wrap items-center gap-2.5">
          <AsyncBoundary resource={invRes}>
            {(investigations) => (
              <Select
                value={selectedInvId ?? "__none__"}
                onValueChange={handleInvChange}
              >
                <SelectTrigger className="w-[200px] h-8 text-xs font-mono bg-surface-2 border-border" aria-label="Select investigation">
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

          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />
            <label htmlFor="timeline-search" className="sr-only">Search events</label>
            <Input
              id="timeline-search"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search event logs…"
              className="h-8 pl-8 text-xs font-mono bg-surface-2 border-border"
            />
          </div>

          <Select value={ch} onValueChange={(v) => setCh(v as ChannelFilter)}>
            <SelectTrigger className="w-[150px] h-8 text-xs font-mono bg-surface-2 border-border" aria-label="Channel filter">
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

          {resource.data && (
            <span className="text-xs font-mono text-muted-foreground ml-auto">
              LOG_EVENTS: {filtered.length}
            </span>
          )}
        </div>
      </Card>

      <div className="mt-4 relative">
        <div
          className="absolute left-3 top-0 bottom-0 w-px bg-border"
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
                      <div className="space-y-2">
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

