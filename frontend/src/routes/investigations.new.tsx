import { createFileRoute, Link, useNavigate, redirect } from "@tanstack/react-router";
import { isAuthenticated } from "@/lib/auth";
import { useState, useEffect } from "react";

import { AppShell } from "@/components/app-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ArrowLeft, Rocket } from "lucide-react";
import { useCreateInvestigation } from "@/hooks/use-osint-data";
import type { IdentifierType, Severity } from "@/types/domain";

export const Route = createFileRoute("/investigations/new")({
  beforeLoad: () => {
    if (!isAuthenticated()) throw redirect({ to: "/auth" });
  },
  head: () => ({ meta: [{ title: "New Investigation — AXIOM OSINT" }] }),
  component: New,
});

function New() {
  const nav = useNavigate();
  const create = useCreateInvestigation();
  const [name, setName] = useState("");
  const [severity, setSeverity] = useState<Severity>("high");
  const [seedType, setSeedType] = useState<IdentifierType>("email");
  const [isSeedTypeManuallySet, setIsSeedTypeManuallySet] = useState(false);
  const [seeds, setSeeds] = useState("");
  const [notes, setNotes] = useState("");

  const canSubmit = name.trim().length > 0 && seeds.trim().length > 0 && !create.isPending;

  const detectIdentifierType = (target: string): IdentifierType => {
    const cleaned = target.trim();
    if (!cleaned) return "domain";
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

  useEffect(() => {
    if (!isSeedTypeManuallySet && seeds.trim()) {
      const firstLine = seeds.split("\n")[0].trim();
      setSeedType(detectIdentifierType(firstLine));
    }
  }, [seeds, isSeedTypeManuallySet]);

  async function handleLaunch() {
    const seedIdentifiers = seeds
      .split("\n")
      .map((s) => s.trim())
      .filter(Boolean);
    if (!name.trim() || seedIdentifiers.length === 0) return;
    
    const finalSeedType = isSeedTypeManuallySet ? seedType : detectIdentifierType(seedIdentifiers[0]);
    
    try {
      const created = await create.mutate({
        name: name.trim(),
        target: seedIdentifiers[0],
        severity,
        seedType: finalSeedType,
        seedIdentifiers,
        notes: notes.trim() || undefined,
      });
      nav({ to: "/investigations/$id", params: { id: created.id } });
    } catch {
      // Error is surfaced via create.error below.
    }
  }

  return (
    <AppShell
      title="Create Case Intake"
      subtitle="Provision a new investigation record and seed target identifiers"
      actions={
        <Link to="/investigations">
          <Button variant="ghost" size="sm" className="gap-1 text-xs font-mono">
            <ArrowLeft className="h-3.5 w-3.5" /> BACK
          </Button>
        </Link>
      }
    >
      <div className="max-w-2xl mx-auto">
        <Card className="p-5 border-border bg-surface rounded-md space-y-4">
          <div className="pb-3 border-b border-border/60">
            <h3 className="font-display text-xs font-bold uppercase tracking-wider text-foreground">Case Parameters</h3>
            <p className="text-[11px] text-muted-foreground mt-0.5">Specify investigation title and priority level</p>
          </div>

          <div>
            <Label htmlFor="case-name" className="text-xs font-mono text-muted-foreground uppercase">Case Title / Mandate</Label>
            <Input id="case-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Operation Nightshade" className="mt-1 bg-surface-2 border-border text-xs h-8" />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <Label className="text-xs font-mono text-muted-foreground uppercase">Severity Level</Label>
              <Select value={severity} onValueChange={(v) => setSeverity(v as Severity)}>
                <SelectTrigger className="mt-1 bg-surface-2 border-border text-xs h-8"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="critical">Critical</SelectItem>
                  <SelectItem value="high">High</SelectItem>
                  <SelectItem value="medium">Medium</SelectItem>
                  <SelectItem value="low">Low</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs font-mono text-muted-foreground uppercase">Seed Entity Type</Label>
              <Select value={seedType} onValueChange={(v) => { setSeedType(v as IdentifierType); setIsSeedTypeManuallySet(true); }}>
                <SelectTrigger className="mt-1 bg-surface-2 border-border text-xs h-8"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="email">Email</SelectItem>
                  <SelectItem value="domain">Domain</SelectItem>
                  <SelectItem value="username">Username</SelectItem>
                  <SelectItem value="wallet">Wallet</SelectItem>
                  <SelectItem value="phone">Phone</SelectItem>
                  <SelectItem value="ip">IP Address</SelectItem>
                  <SelectItem value="mac">MAC / BSSID Address</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div>
            <Label htmlFor="seeds" className="text-xs font-mono text-muted-foreground uppercase">Seed Identifiers (one per line)</Label>
            <Textarea id="seeds" rows={4} value={seeds} onChange={(e) => setSeeds(e.target.value)} placeholder="j.doe@protonmail.com&#10;secure-login-verify.io" className="mt-1 bg-surface-2 border-border font-mono text-xs p-2.5" />
          </div>

          <div>
            <Label htmlFor="notes" className="text-xs font-mono text-muted-foreground uppercase">Analyst Notes & Context</Label>
            <Textarea id="notes" rows={3} value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Investigator context, mandates, TLP classification..." className="mt-1 bg-surface-2 border-border text-xs p-2.5" />
          </div>

          {create.error && (
            <div role="alert" className="text-xs font-mono text-destructive bg-destructive/10 border border-destructive/30 rounded-sm p-2">
              {create.error.message}
            </div>
          )}

          <div className="flex items-center justify-end gap-2 pt-3 border-t border-border/60">
            <Button variant="ghost" size="sm" className="text-xs font-mono" onClick={() => nav({ to: "/investigations" })}>Cancel</Button>
            <Button
              size="sm"
              onClick={handleLaunch}
              disabled={!canSubmit}
              className="bg-primary text-primary-foreground hover:bg-primary/90 gap-1.5 font-mono text-xs"
            >
              <Rocket className="h-3.5 w-3.5" /> {create.isPending ? "LAUNCHING…" : "LAUNCH CASE"}
            </Button>
          </div>
        </Card>
      </div>
    </AppShell>
  );
}

