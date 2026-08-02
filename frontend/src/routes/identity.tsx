import { createFileRoute } from "@tanstack/react-router";
import { AppShell } from "@/components/app-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Mail, Globe, User, Wallet, Share2, Phone, Server, Shield, Copy, ExternalLink } from "lucide-react";
import { AsyncBoundary } from "@/components/states";
import { ConfidenceBar, formatConfidencePercent } from "@/components/confidence-bar";
import { MetricPill } from "@/components/field";
import { useIdentityProfile } from "@/hooks/use-osint-data";
import type { IdentitySection, IdentitySectionKey } from "@/types/domain";

export const Route = createFileRoute("/identity")({
  head: () => ({ meta: [{ title: "Identity Profile — AXIOM OSINT" }] }),
  component: Identity,
});

const sectionIcon: Record<IdentitySectionKey, typeof Mail> = {
  emails: Mail,
  domains: Globe,
  usernames: User,
  wallets: Wallet,
  social: Share2,
  phones: Phone,
  network: Server,
};

function SectionCard({ section }: { section: IdentitySection }) {
  const Icon = sectionIcon[section.key];
  return (
    <Card className="glass p-5 border-border/60">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-lg bg-primary/10 text-primary grid place-items-center" aria-hidden="true">
            <Icon className="h-4 w-4" />
          </div>
          <h3 className="font-display font-semibold">{section.title}</h3>
          <span className="text-xs text-muted-foreground">({section.items.length})</span>
        </div>
      </div>
      <div className="mt-3 divide-y divide-border/40">
        {section.items.map((it) => (
          <div key={it.value} className="py-3 flex items-center gap-3">
            <div className="min-w-0 flex-1">
              <div className="font-mono text-xs truncate">{it.value}</div>
              <div className="text-[10px] text-muted-foreground mt-0.5">{it.note}</div>
            </div>
            <div className="hidden sm:block w-28">
              <ConfidenceBar
                value={it.confidence}
                valueWidthClass="w-6"
                ariaLabel={`Confidence for ${it.value}`}
              />
              <div className="text-[10px] text-muted-foreground mt-0.5 text-right">{it.sources} src</div>
            </div>
            <div className="flex items-center gap-1">
              <Button variant="ghost" size="icon" className="h-7 w-7" aria-label={`Copy ${it.value}`}>
                <Copy className="h-3 w-3" aria-hidden="true" />
              </Button>
              <Button variant="ghost" size="icon" className="h-7 w-7" aria-label={`Open ${it.value}`}>
                <ExternalLink className="h-3 w-3" aria-hidden="true" />
              </Button>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

function Identity() {
  const resource = useIdentityProfile();

  return (
    <AppShell
      title="Unified Identity Profile"
      subtitle="Aggregated view of every observed identifier for the primary target"
    >
      <AsyncBoundary resource={resource}>
        {(profile) => (
          <>
            {/* Subject header */}
            <Card className="glass border-border/60 overflow-hidden">
              <div className="relative p-6">
                <div className="absolute inset-0 opacity-30 gradient-text" aria-hidden="true" />
                <div className="relative flex flex-wrap items-center gap-4">
                  <div className="relative">
                    <div className="absolute inset-0 rounded-full blur-lg opacity-70 bg-gradient-to-br from-primary to-accent" aria-hidden="true" />
                    <div className="relative h-16 w-16 rounded-full bg-gradient-to-br from-primary to-accent grid place-items-center text-2xl font-display font-bold text-primary-foreground">
                      {profile.initials}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs uppercase tracking-widest text-muted-foreground">Subject</div>
                    <div className="text-xl font-display font-semibold">{profile.displayName}</div>
                    <div className="text-xs text-muted-foreground font-mono mt-0.5">
                      {profile.subjectId} · linked to {profile.linkedInvestigation}
                    </div>
                  </div>
                  <div className="ml-auto flex flex-wrap gap-2">
                    <MetricPill label="Total identifiers" value={String(profile.totalIdentifiers)} />
                    <MetricPill label="Sources" value={String(profile.totalSources)} />
                    <MetricPill label="Overall confidence" value={`${formatConfidencePercent(profile.overallConfidence)}%`} tone="success" />
                  </div>
                </div>
              </div>
            </Card>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-4">
              {profile.sections.map((sec) => (
                <SectionCard key={sec.key} section={sec} />
              ))}
            </div>

            {/* Evidence */}
            <Card className="glass p-5 border-border/60 mt-4">
              <div className="flex items-center gap-2 mb-3">
                <Shield className="h-4 w-4 text-primary" aria-hidden="true" />
                <h3 className="font-display font-semibold">Evidence Chain</h3>
              </div>
              <div className="space-y-2 text-xs">
                {profile.evidence.map((e, i) => (
                  <div key={i} className="flex items-center gap-3 p-3 rounded-lg bg-white/[0.03] border border-border/40">
                    <span className="text-[10px] uppercase tracking-widest text-muted-foreground w-32 shrink-0">{e.src}</span>
                    <span className="flex-1 min-w-0">{e.finding}</span>
                    <span className="text-[10px] font-mono text-primary">conf {e.conf}%</span>
                  </div>
                ))}
              </div>
            </Card>
          </>
        )}
      </AsyncBoundary>
    </AppShell>
  );
}
