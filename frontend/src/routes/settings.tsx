import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { toast } from "sonner";
import { AppShell } from "@/components/app-shell";
import { Card } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  useNotificationPrefs,
  useThemeSettings,
} from "@/hooks/use-settings";
import { getUser } from "@/lib/auth";
import { Palette, User, Bell, Check, Sun, Moon, Mail, ShieldCheck } from "lucide-react";

export const Route = createFileRoute("/settings")({
  head: () => ({ meta: [{ title: "Settings — AXIOM OSINT" }] }),
  component: Settings,
});

const themePresets: ReadonlyArray<{ name: string; primary: string; accent: string }> = [
  { name: "Cobalt Titanium", primary: "oklch(0.72 0.14 220)", accent: "oklch(0.68 0.14 190)" },
  { name: "Crimson Red", primary: "oklch(0.65 0.22 25)", accent: "oklch(0.70 0.18 45)" },
  { name: "Emerald Green", primary: "oklch(0.72 0.18 150)", accent: "oklch(0.70 0.15 180)" },
  { name: "Amber Ochre", primary: "oklch(0.75 0.18 80)", accent: "oklch(0.70 0.15 60)" },
];

function ProfileSection() {
  const user = getUser();

  return (
    <Card className="p-4 border-border bg-surface rounded-md">
      <div className="flex items-center gap-2 pb-2 border-b border-border/60 mb-3">
        <User className="h-4 w-4 text-primary" aria-hidden="true" />
        <h3 className="font-display text-xs font-bold uppercase tracking-wider text-foreground">Analyst Credentials</h3>
      </div>
      
      {user ? (
        <div className="space-y-3 font-mono text-xs">
          <div className="flex items-center gap-3 p-3 rounded-sm bg-surface-2 border border-border">
            <div className="h-9 w-9 rounded-sm bg-surface-3 border border-border grid place-items-center text-sm font-bold text-primary shrink-0">
              {user.email[0].toUpperCase()}
            </div>
            <div className="flex-1 min-w-0 font-sans">
              <div className="flex items-center gap-2">
                <Mail className="h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />
                <span className="text-xs font-mono font-bold text-foreground">{user.email}</span>
              </div>
              {user.fullName && (
                <div className="text-xs text-muted-foreground mt-0.5">{user.fullName}</div>
              )}
            </div>
            {user.isVerified && (
              <span className="text-[9px] font-mono font-bold uppercase tracking-widest text-success bg-success/10 border border-success/30 px-2 py-0.5 rounded-sm flex items-center gap-1">
                <ShieldCheck className="h-3 w-3" /> VERIFIED
              </span>
            )}
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
            <div className="p-2.5 rounded-sm bg-surface-2 border border-border">
              <div className="text-[9px] uppercase tracking-widest text-muted-foreground">Account Identifier</div>
              <div className="font-bold text-foreground mt-0.5 truncate">{user.id}</div>
            </div>
            <div className="p-2.5 rounded-sm bg-surface-2 border border-border">
              <div className="text-[9px] uppercase tracking-widest text-muted-foreground">Provisioned Date</div>
              <div className="font-bold text-foreground mt-0.5">{new Date(user.createdAt).toLocaleDateString()}</div>
            </div>
          </div>
        </div>
      ) : (
        <div className="p-3 rounded-sm bg-surface-2 border border-border text-xs font-mono text-muted-foreground">
          No session active. Please authenticate.
        </div>
      )}
    </Card>
  );
}

function AppearanceSection() {
  const { theme, setPreset, mode, setMode } = useThemeSettings();

  const handleSelectPreset = (name: string) => {
    const preset = themePresets.find((p) => p.name === name);
    if (preset) {
      setPreset(name, preset.primary, preset.accent);
      toast.success(`Switched to ${name} palette`);
    }
  };

  const handleModeChange = (newMode: "light" | "dark") => {
    setMode(newMode);
    toast.success(`Switched to ${newMode} mode`);
  };

  return (
    <Card className="p-4 border-border bg-surface rounded-md">
      <div className="flex items-center gap-2 pb-2 border-b border-border/60 mb-3">
        <Palette className="h-4 w-4 text-primary" aria-hidden="true" />
        <h3 className="font-display text-xs font-bold uppercase tracking-wider text-foreground">Console Theme & Accent</h3>
      </div>
      
      {/* Mode choice */}
      <div className="mb-4">
        <Label className="text-xs font-mono text-muted-foreground uppercase">Display Mode</Label>
        <div className="mt-1.5 grid grid-cols-2 gap-2 font-mono text-xs">
          <button
            className={`p-2.5 rounded-sm border ${mode === "dark" ? "border-primary bg-primary/10 text-foreground font-bold" : "border-border bg-surface-2 text-muted-foreground"} flex items-center justify-center gap-2`}
            onClick={() => handleModeChange("dark")}
          >
            <Moon className="h-3.5 w-3.5" />
            <span>Dark Workstation</span>
            {mode === "dark" && <Check className="h-3.5 w-3.5 ml-auto text-primary" />}
          </button>
          <button
            className={`p-2.5 rounded-sm border ${mode === "light" ? "border-primary bg-primary/10 text-foreground font-bold" : "border-border bg-surface-2 text-muted-foreground"} flex items-center justify-center gap-2`}
            onClick={() => handleModeChange("light")}
          >
            <Sun className="h-3.5 w-3.5" />
            <span>Light Terminal</span>
            {mode === "light" && <Check className="h-3.5 w-3.5 ml-auto text-primary" />}
          </button>
        </div>
      </div>

      {/* Preset choice */}
      <div>
        <Label className="text-xs font-mono text-muted-foreground uppercase">Tactical Color Preset</Label>
        <div className="mt-1.5 grid grid-cols-2 md:grid-cols-4 gap-2 font-mono text-xs">
          {themePresets.map(({ name }) => {
            const active = theme.preset === name;
            return (
              <button
                key={name}
                className={`p-2.5 rounded-sm border text-left ${active ? "border-primary bg-primary/10 text-foreground font-bold" : "border-border bg-surface-2 text-muted-foreground"}`}
                onClick={() => handleSelectPreset(name)}
              >
                <div className="flex items-center justify-between">
                  <span>{name}</span>
                  {active && <Check className="h-3 w-3 text-primary" />}
                </div>
              </button>
            );
          })}
        </div>
      </div>
    </Card>
  );
}

function NotificationsSection() {
  const { prefs, toggle } = useNotificationPrefs();
  const [notificationsEnabled, setNotificationsEnabled] = useState(prefs.investigationUpdates);

  const handleToggle = () => {
    const newState = !notificationsEnabled;
    setNotificationsEnabled(newState);
    if (prefs.investigationUpdates !== newState) {
      toggle("investigationUpdates");
    }
    toast.info(newState ? "Telemetry alerts enabled" : "Telemetry alerts muted");
  };

  return (
    <Card className="p-4 border-border bg-surface rounded-md">
      <div className="flex items-center gap-2 pb-2 border-b border-border/60 mb-3">
        <Bell className="h-4 w-4 text-primary" aria-hidden="true" />
        <h3 className="font-display text-xs font-bold uppercase tracking-wider text-foreground">Alert Preferences</h3>
      </div>
      
      <div className="flex items-center justify-between p-3 rounded-sm bg-surface-2 border border-border">
        <div>
          <div className="text-xs font-semibold text-foreground font-sans">Execution & System Alerts</div>
          <div className="text-[11px] font-mono text-muted-foreground mt-0.5">
            Receive real-time push events when connector runs finish or fail
          </div>
        </div>
        <Switch
          checked={notificationsEnabled}
          onCheckedChange={handleToggle}
          aria-label="Toggle notifications"
        />
      </div>
    </Card>
  );
}

function Settings() {
  return (
    <AppShell 
      title="System Preferences" 
      subtitle="Configure analyst account settings, workstation theme, and telemetry alerts"
    >
      <div className="max-w-3xl space-y-3">
        <ProfileSection />
        <AppearanceSection />
        <NotificationsSection />
      </div>
    </AppShell>
  );
}

