import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { AppShell } from "@/components/app-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { StatusBadge } from "@/components/badges";
import { AsyncBoundary } from "@/components/states";
import { useConnectors } from "@/hooks/use-osint-data";
import { Key, Palette, User, Bell, Save, Eye, EyeOff, Plus } from "lucide-react";

export const Route = createFileRoute("/settings")({
  head: () => ({ meta: [{ title: "Settings — AXIOM OSINT" }] }),
  component: Settings,
});

interface ApiKeyEntry {
  name: string;
  key: string;
  created: string;
  used: string;
}

// TODO(api): replace with `useApiKeys()` hook against the FastAPI backend.
const apiKeys: ApiKeyEntry[] = [
  { name: "Production", key: "axm_live_9f2a3b4c5d6e7f8a9b0c1d2e", created: "2026-04-11", used: "2 min ago" },
  { name: "CI Pipeline", key: "axm_live_1a2b3c4d5e6f7g8h9i0j1k2l", created: "2026-05-02", used: "3 hours ago" },
];

const themePresets: ReadonlyArray<{ name: string; gradient: string; active: boolean }> = [
  { name: "Cyan · Violet", gradient: "from-primary to-accent", active: true },
  { name: "Ember", gradient: "from-orange-400 to-red-500", active: false },
  { name: "Emerald", gradient: "from-emerald-400 to-teal-500", active: false },
  { name: "Rose", gradient: "from-pink-400 to-fuchsia-500", active: false },
];

const notificationPreferences: ReadonlyArray<{ label: string; sub: string }> = [
  { label: "Critical alerts", sub: "Instant desktop + email" },
  { label: "Connector failures", sub: "Email digest" },
  { label: "Investigation updates", sub: "In-app only" },
  { label: "Weekly intel digest", sub: "Every Monday 09:00" },
];

function ApiKeyRow({ entry }: { entry: ApiKeyEntry }) {
  const [show, setShow] = useState(false);
  return (
    <div className="flex items-center gap-3 p-4 rounded-xl bg-surface/60 border border-border/60">
      <div className="min-w-0 flex-1">
        <div className="font-medium text-sm">{entry.name}</div>
        <div className="mt-1 flex items-center gap-2">
          <code className="font-mono text-xs text-muted-foreground">
            {show ? entry.key : entry.key.slice(0, 12) + "•".repeat(16)}
          </code>
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6"
            onClick={() => setShow((s) => !s)}
            aria-label={show ? "Hide API key" : "Show API key"}
            aria-pressed={show}
          >
            {show ? <EyeOff className="h-3 w-3" aria-hidden="true" /> : <Eye className="h-3 w-3" aria-hidden="true" />}
          </Button>
        </div>
      </div>
      <div className="text-xs text-muted-foreground text-right">
        <div>Created {entry.created}</div>
        <div>Last used {entry.used}</div>
      </div>
      <Button variant="ghost" size="sm" className="text-destructive">Revoke</Button>
    </div>
  );
}

function ProfileField({ label, value }: { label: string; value: string }) {
  const id = `profile-${label.replace(/\s+/g, "-").toLowerCase()}`;
  return (
    <div>
      <Label htmlFor={id}>{label}</Label>
      <Input id={id} defaultValue={value} className="mt-1.5 bg-surface/60" />
    </div>
  );
}

function Settings() {
  const connectorsRes = useConnectors();

  return (
    <AppShell title="Settings" subtitle="Manage keys, connectors, profile, and appearance">
      <Tabs defaultValue="keys">
        <TabsList className="bg-surface/60 border border-border/60">
          <TabsTrigger value="keys"><Key className="h-3.5 w-3.5 mr-1.5" aria-hidden="true" /> API Keys</TabsTrigger>
          <TabsTrigger value="connectors">Connectors</TabsTrigger>
          <TabsTrigger value="profile"><User className="h-3.5 w-3.5 mr-1.5" aria-hidden="true" /> Profile</TabsTrigger>
          <TabsTrigger value="theme"><Palette className="h-3.5 w-3.5 mr-1.5" aria-hidden="true" /> Theme</TabsTrigger>
          <TabsTrigger value="notifications"><Bell className="h-3.5 w-3.5 mr-1.5" aria-hidden="true" /> Notifications</TabsTrigger>
        </TabsList>

        <TabsContent value="keys">
          <Card className="glass p-6 border-border/60">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="font-display text-lg font-semibold">API Keys</h3>
                <p className="text-sm text-muted-foreground">Personal access tokens for the AXIOM REST API.</p>
              </div>
              <Button className="gap-2 bg-gradient-to-r from-primary to-accent text-primary-foreground">
                <Plus className="h-4 w-4" aria-hidden="true" /> New key
              </Button>
            </div>
            <div className="mt-5 space-y-3">
              {apiKeys.map((k) => <ApiKeyRow key={k.key} entry={k} />)}
            </div>
          </Card>
        </TabsContent>

        <TabsContent value="connectors">
          <Card className="glass p-6 border-border/60">
            <h3 className="font-display text-lg font-semibold">Connectors</h3>
            <p className="text-sm text-muted-foreground">Enable, configure, and rate-limit third-party intelligence sources.</p>
            <AsyncBoundary resource={connectorsRes}>
              {(list) => (
                <div className="mt-4 divide-y divide-border/60">
                  {list.slice(0, 8).map((c) => (
                    <div key={c.id} className="py-3 flex items-center gap-4">
                      <div className="h-9 w-9 rounded-lg bg-primary/10 text-primary grid place-items-center font-display font-bold text-xs" aria-hidden="true">
                        {c.name.slice(0, 2).toUpperCase()}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="font-medium text-sm">{c.name}</div>
                        <div className="text-xs text-muted-foreground">{c.category}</div>
                      </div>
                      <StatusBadge status={c.status} />
                      <Switch defaultChecked={c.status !== "failed"} aria-label={`Enable ${c.name}`} />
                    </div>
                  ))}
                </div>
              )}
            </AsyncBoundary>
          </Card>
        </TabsContent>

        <TabsContent value="profile">
          <Card className="glass p-6 border-border/60 max-w-2xl">
            <h3 className="font-display text-lg font-semibold">Profile</h3>
            <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
              <ProfileField label="Full name" value="Mei Chen" />
              <ProfileField label="Role" value="Senior Analyst" />
              <ProfileField label="Email" value="m.chen@axiom-intel.io" />
              <ProfileField label="Clearance" value="TLP:AMBER" />
            </div>
            <div className="mt-6 flex justify-end">
              <Button className="gap-2 bg-gradient-to-r from-primary to-accent text-primary-foreground">
                <Save className="h-4 w-4" aria-hidden="true" /> Save
              </Button>
            </div>
          </Card>
        </TabsContent>

        <TabsContent value="theme">
          <Card className="glass p-6 border-border/60 max-w-2xl">
            <h3 className="font-display text-lg font-semibold">Appearance</h3>
            <p className="text-sm text-muted-foreground">Cinematic obsidian by default. Accent color drives glow and highlights.</p>
            <div className="mt-5 grid grid-cols-4 gap-3">
              {themePresets.map(({ name, gradient, active }) => (
                <button
                  key={name}
                  className={`rounded-xl p-3 border ${active ? "border-primary ring-2 ring-primary/40" : "border-border/60"} bg-surface/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40`}
                  aria-pressed={active}
                >
                  <div className={`h-16 rounded-lg bg-gradient-to-br ${gradient}`} aria-hidden="true" />
                  <div className="mt-2 text-xs">{name}</div>
                </button>
              ))}
            </div>
          </Card>
        </TabsContent>

        <TabsContent value="notifications">
          <Card className="glass p-6 border-border/60 max-w-2xl">
            <h3 className="font-display text-lg font-semibold">Notifications</h3>
            <div className="mt-4 space-y-3">
              {notificationPreferences.map(({ label, sub }) => (
                <div key={label} className="flex items-center gap-3 p-3 rounded-lg bg-surface/60 border border-border/60">
                  <div className="flex-1">
                    <div className="text-sm font-medium">{label}</div>
                    <div className="text-xs text-muted-foreground">{sub}</div>
                  </div>
                  <Switch defaultChecked aria-label={label} />
                </div>
              ))}
            </div>
          </Card>
        </TabsContent>
      </Tabs>
    </AppShell>
  );
}
