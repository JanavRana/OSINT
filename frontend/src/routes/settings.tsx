import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { toast } from "sonner";
import { AppShell } from "@/components/app-shell";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  useProfileSettings,
  useNotificationPrefs,
  useThemeSettings,
  type ProfileSettings,
} from "@/hooks/use-settings";
import { Palette, User, Bell, Save, Check, Monitor, Sun, Moon } from "lucide-react";

export const Route = createFileRoute("/settings")({
  head: () => ({ meta: [{ title: "Settings — AXIOM OSINT" }] }),
  component: Settings,
});

const themePresets: ReadonlyArray<{ name: string; gradient: string; primary: string; accent: string }> = [
  { name: "Cyan · Violet", gradient: "from-primary to-accent", primary: "oklch(0.82 0.17 195)", accent: "oklch(0.65 0.24 295)" },
  { name: "Ember", gradient: "from-orange-400 to-red-500", primary: "oklch(0.78 0.20 45)", accent: "oklch(0.65 0.26 25)" },
  { name: "Emerald", gradient: "from-emerald-400 to-teal-500", primary: "oklch(0.78 0.17 155)", accent: "oklch(0.65 0.18 185)" },
  { name: "Rose", gradient: "from-pink-400 to-fuchsia-500", primary: "oklch(0.76 0.21 340)", accent: "oklch(0.65 0.28 320)" },
];

const notifKeys: { label: string; sub: string; key: keyof ReturnType<typeof useNotificationPrefs>["prefs"] }[] = [
  { label: "Critical alerts", sub: "Instant desktop + email", key: "criticalAlerts" },
  { label: "Connector failures", sub: "Email digest", key: "connectorFailures" },
  { label: "Investigation updates", sub: "In-app only", key: "investigationUpdates" },
  { label: "Weekly intel digest", sub: "Every Monday 09:00", key: "weeklyDigest" },
];

// ─── Profile tab ──────────────────────────────────────────────────────────────

function ProfileTab() {
  const { profile, saveProfile } = useProfileSettings();
  const [local, setLocal] = useState<ProfileSettings>({ ...profile });
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    // Auto-derive initials from full name
    const initials = local.fullName
      .split(" ")
      .map((n) => n[0])
      .slice(0, 2)
      .join("")
      .toUpperCase();
    saveProfile({ ...local, initials });
    setSaved(true);
    toast.success("Profile saved", { description: "Your profile settings have been updated." });
    setTimeout(() => setSaved(false), 2000);
  };

  const fields: { label: string; key: keyof ProfileSettings; type?: string }[] = [
    { label: "Full name", key: "fullName" },
    { label: "Role", key: "role" },
    { label: "Email", key: "email", type: "email" },
    { label: "Clearance", key: "clearance" },
  ];

  return (
    <Card className="glass p-6 border-border/60 max-w-2xl">
      <h3 className="font-display text-lg font-semibold">Profile</h3>
      <p className="text-sm text-muted-foreground mt-1">
        Your profile is persisted locally. It sets your display name in the UI.
      </p>
      <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
        {fields.map(({ label, key, type }) => {
          const id = `profile-${key}`;
          return (
            <div key={key}>
              <Label htmlFor={id}>{label}</Label>
              <Input
                id={id}
                type={type ?? "text"}
                value={local[key]}
                onChange={(e) => setLocal((prev) => ({ ...prev, [key]: e.target.value }))}
                className="mt-1.5 bg-surface/60"
              />
            </div>
          );
        })}
      </div>
      <div className="mt-6 flex justify-end">
        <Button
          className="gap-2 bg-gradient-to-r from-primary to-accent text-primary-foreground"
          onClick={handleSave}
        >
          {saved ? (
            <Check className="h-4 w-4" aria-hidden="true" />
          ) : (
            <Save className="h-4 w-4" aria-hidden="true" />
          )}
          {saved ? "Saved!" : "Save"}
        </Button>
      </div>
    </Card>
  );
}

// ─── Theme tab ────────────────────────────────────────────────────────────────

function ThemeTab() {
  const { theme, setPreset, mode, setMode } = useThemeSettings();

  const handleSelectPreset = (name: string) => {
    const preset = themePresets.find((p) => p.name === name);
    if (preset) {
      setPreset(name, preset.primary, preset.accent);
      toast.success("Theme updated", { description: `Switched to ${name} preset.` });
    }
  };

  const handleModeChange = (newMode: "light" | "dark") => {
    setMode(newMode);
    toast.success("Theme mode updated", { description: `Switched to ${newMode} mode.` });
  };

  return (
    <Card className="glass p-6 border-border/60 max-w-2xl">
      <h3 className="font-display text-lg font-semibold">Appearance</h3>
      <p className="text-sm text-muted-foreground">Customize theme mode and accent colors.</p>
      
      {/* Theme mode selector */}
      <div className="mt-5">
        <Label className="text-sm font-medium">Theme Mode</Label>
        <div className="mt-2 grid grid-cols-2 gap-3">
          <button
            className={`rounded-xl p-4 border ${mode === "dark" ? "border-primary ring-2 ring-primary/40" : "border-border/60"} bg-surface/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 transition-all flex items-center justify-center gap-2`}
            aria-pressed={mode === "dark"}
            onClick={() => handleModeChange("dark")}
          >
            <Moon className="h-4 w-4" aria-hidden="true" />
            <span className="text-sm font-medium">Dark</span>
            {mode === "dark" && <Check className="h-4 w-4 ml-auto text-primary" />}
          </button>
          <button
            className={`rounded-xl p-4 border ${mode === "light" ? "border-primary ring-2 ring-primary/40" : "border-border/60"} bg-surface/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 transition-all flex items-center justify-center gap-2`}
            aria-pressed={mode === "light"}
            onClick={() => handleModeChange("light")}
          >
            <Sun className="h-4 w-4" aria-hidden="true" />
            <span className="text-sm font-medium">Light</span>
            {mode === "light" && <Check className="h-4 w-4 ml-auto text-primary" />}
          </button>
        </div>
      </div>

      {/* Accent color presets */}
      <div className="mt-5">
        <Label className="text-sm font-medium">Accent Color</Label>
        <div className="mt-2 grid grid-cols-4 gap-3">
          {themePresets.map(({ name, gradient }) => {
            const active = theme.preset === name;
            return (
              <button
                key={name}
                className={`rounded-xl p-3 border ${active ? "border-primary ring-2 ring-primary/40" : "border-border/60"} bg-surface/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 transition-all`}
                aria-pressed={active}
                onClick={() => handleSelectPreset(name)}
              >
                <div className={`h-16 rounded-lg bg-gradient-to-br ${gradient} relative`} aria-hidden="true">
                  {active && (
                    <div className="absolute top-1 right-1 h-5 w-5 rounded-full bg-white/90 grid place-items-center">
                      <Check className="h-3 w-3 text-foreground" />
                    </div>
                  )}
                </div>
                <div className="mt-2 text-xs">{name}</div>
              </button>
            );
          })}
        </div>
      </div>
    </Card>
  );
}

// ─── Notifications tab ────────────────────────────────────────────────────────

function NotificationsTab() {
  const { prefs, toggle } = useNotificationPrefs();

  const handleToggle = (key: keyof typeof prefs) => {
    toggle(key);
    toast.info("Notification preference updated");
  };

  return (
    <Card className="glass p-6 border-border/60 max-w-2xl">
      <h3 className="font-display text-lg font-semibold">Notifications</h3>
      <p className="text-sm text-muted-foreground mt-1">
        Preferences are saved locally. Investigation status changes are polled every 30 seconds.
      </p>
      <div className="mt-4 space-y-3">
        {notifKeys.map(({ label, sub, key }) => (
          <div key={key} className="flex items-center gap-3 p-3 rounded-lg bg-surface/60 border border-border/60">
            <div className="flex-1">
              <div className="text-sm font-medium">{label}</div>
              <div className="text-xs text-muted-foreground">{sub}</div>
            </div>
            <Switch
              checked={prefs[key]}
              onCheckedChange={() => handleToggle(key)}
              aria-label={label}
            />
          </div>
        ))}
      </div>
    </Card>
  );
}

// ─── Settings page ────────────────────────────────────────────────────────────

function Settings() {
  return (
    <AppShell title="Settings" subtitle="Manage profile, appearance, and notifications">
      <Tabs defaultValue="profile">
        <TabsList className="bg-surface/60 border border-border/60">
          <TabsTrigger value="profile"><User className="h-3.5 w-3.5 mr-1.5" aria-hidden="true" /> Profile</TabsTrigger>
          <TabsTrigger value="theme"><Palette className="h-3.5 w-3.5 mr-1.5" aria-hidden="true" /> Theme</TabsTrigger>
          <TabsTrigger value="notifications"><Bell className="h-3.5 w-3.5 mr-1.5" aria-hidden="true" /> Notifications</TabsTrigger>
        </TabsList>

        <TabsContent value="profile">
          <ProfileTab />
        </TabsContent>

        <TabsContent value="theme">
          <ThemeTab />
        </TabsContent>

        <TabsContent value="notifications">
          <NotificationsTab />
        </TabsContent>
      </Tabs>
    </AppShell>
  );
}
