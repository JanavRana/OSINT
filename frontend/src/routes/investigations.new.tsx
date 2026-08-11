import { createFileRoute, Link, useNavigate, redirect } from "@tanstack/react-router";
import { isAuthenticated } from "@/lib/auth";
import { useState } from "react";
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
    // IPv6: contains colons and hex digits (also handles compressed forms like ::1)
    if (cleaned.includes(":") && /^[0-9a-fA-F:]+$/.test(cleaned) && cleaned.includes(":")) return "ip";
    if (cleaned.match(/^\+?\d+$/)) return "phone";
    if (cleaned.startsWith("@")) return "username";
    return "domain";
  };

  async function handleLaunch() {
    const seedIdentifiers = seeds
      .split("\n")
      .map((s) => s.trim())
      .filter(Boolean);
    if (!name.trim() || seedIdentifiers.length === 0) return;
    
    // Auto-detect seed type if user hasn't explicitly changed the default dropdown selection
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
      title="Create Investigation"
      subtitle="Seed a new case with one or more identifiers"
      actions={
        <Link to="/investigations">
          <Button variant="ghost" className="gap-2"><ArrowLeft className="h-4 w-4" /> Back</Button>
        </Link>
      }
    >
      <div className="max-w-3xl mx-auto">
        <Card className="glass p-6 border-border/60 space-y-5">
          <div>
            <Label htmlFor="case-name">Case name</Label>
            <Input id="case-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Operation Nightshade" className="mt-1.5 bg-surface/60" />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label>Severity</Label>
              <Select value={severity} onValueChange={(v) => setSeverity(v as Severity)}>
                <SelectTrigger className="mt-1.5 bg-surface/60"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="critical">Critical</SelectItem>
                  <SelectItem value="high">High</SelectItem>
                  <SelectItem value="medium">Medium</SelectItem>
                  <SelectItem value="low">Low</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Seed identifier type</Label>
              <Select value={seedType} onValueChange={(v) => { setSeedType(v as IdentifierType); setIsSeedTypeManuallySet(true); }}>
                <SelectTrigger className="mt-1.5 bg-surface/60"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="email">Email</SelectItem>
                  <SelectItem value="domain">Domain</SelectItem>
                  <SelectItem value="username">Username</SelectItem>
                  <SelectItem value="wallet">Wallet</SelectItem>
                  <SelectItem value="phone">Phone</SelectItem>
                  <SelectItem value="ip">IP Address</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <div>
            <Label htmlFor="seeds">Seed identifiers</Label>
            <Textarea id="seeds" rows={4} value={seeds} onChange={(e) => setSeeds(e.target.value)} placeholder="one per line, e.g.&#10;j.doe@protonmail.com&#10;secure-login-verify.io" className="mt-1.5 bg-surface/60 font-mono text-xs" />
          </div>
          <div>
            <Label htmlFor="notes">Notes</Label>
            <Textarea id="notes" rows={3} value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Investigator context, mandates, TLP…" className="mt-1.5 bg-surface/60" />
          </div>

          {create.error && (
            <div role="alert" className="text-xs text-destructive">
              {create.error.message}
            </div>
          )}

          <div className="flex items-center justify-end gap-2 pt-2 border-t border-border/60">
            <Button variant="ghost" onClick={() => nav({ to: "/investigations" })}>Cancel</Button>
            <Button
              onClick={handleLaunch}
              disabled={!canSubmit}
              className="bg-gradient-to-r from-primary to-accent text-primary-foreground gap-2"
            >
              <Rocket className="h-4 w-4" /> {create.isPending ? "Launching…" : "Launch Investigation"}
            </Button>
          </div>
        </Card>
      </div>
    </AppShell>
  );
}
