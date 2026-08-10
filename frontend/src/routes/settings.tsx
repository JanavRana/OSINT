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
import { Palette, User, Bell, Check, Sun, Moon, Mail } from "lucide-react";

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

// ─── Profile section ──────────────────────────────────────────────────────────

function ProfileSection() {
  const user = getUser();

  return (
    <Card className="glass p-6 border-border/60">
      <div className="flex items-center gap-2 mb-4">
        <User className="h-4 w-4 text-primary" aria-hidden="true" />
        <h3 className="font-display text-lg font-semibold">Profile</h3>
      </div>
      <p className="text-sm text-muted-foreground mb-4">
        Your authenticated account information.
      </p>
      
      {user ? (
        <div className="space-y-4">
          <div className="flex items-center gap-3 p-4 rounded-lg bg-surface/60 border border-border/60">
            <div className="h-10 w-10 rounded-full bg-gradient-to-br from-primary to-accent grid place-items-center text-sm font-display font-bold text-primary-foreground">
              {user.email[0].toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <Mail className="h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />
                <span className="text-sm font-mono">{user.email}</span>
              </div>
              {user.fullName && (
                <div className="text-xs text-muted-foreground mt-1">{user.fullName}</div>
              )}
            </div>
            {user.isVerified && (
              <Check className="h-4 w-4 text-success" aria-label="Verified" />
            )}
          </div>
          
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="p-3 rounded-lg bg-surface/60 border border-border/60">
              <div className="text-muted-foreground">Account ID</div>
              <div className="font-mono mt-1 truncate">{user.id}</div>
            </div>
            <div className="p-3 rounded-lg bg-surface/60 border border-border/60">
              <div className="text-muted-foreground">Created</div>
              <div className="font-mono mt-1">{new Date(user.createdAt).toLocaleDateString()}</div>
            </div>
          </div>
        </div>
      ) : (
        <div className="p-4 rounded-lg bg-surface/60 border border-border/60 text-sm text-muted-foreground">
          No user data available. Please log in.
        </div>
      )}
    </Card>
  );
}

// ─── Appearance section ───────────────────────────────────────────────────────

function AppearanceSection() {
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
    <Card className="glass p-6 border-border/60">
      <div className="flex items-center gap-2 mb-4">
        <Palette className="h-4 w-4 text-primary" aria-hidden="true" />
        <h3 className="font-display text-lg font-semibold">Appearance</h3>
      </div>
      <p className="text-sm text-muted-foreground mb-5">
        Customize theme mode and accent colors.
      </p>
      
      {/* Theme mode selector */}
      <div className="mb-5">
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
      <div>
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

// ─── Notifications section ────────────────────────────────────────────────────

function NotificationsSection() {
  const { prefs, toggle } = useNotificationPrefs();
  const [notificationsEnabled, setNotificationsEnabled] = useState(prefs.investigationUpdates);

  const handleToggle = () => {
    const newState = !notificationsEnabled;
    setNotificationsEnabled(newState);
    
    // Update the actual preference
    if (prefs.investigationUpdates !== newState) {
      toggle("investigationUpdates");
    }
    
    toast.info(
      newState ? "Notifications enabled" : "Notifications disabled",
      { description: newState ? "You'll receive investigation status updates" : "Notifications are now silent" }
    );
  };

  return (
    <Card className="glass p-6 border-border/60">
      <div className="flex items-center gap-2 mb-4">
        <Bell className="h-4 w-4 text-primary" aria-hidden="true" />
        <h3 className="font-display text-lg font-semibold">Notifications</h3>
      </div>
      <p className="text-sm text-muted-foreground mb-4">
        Control investigation status notifications.
      </p>
      
      <div className="flex items-center justify-between p-4 rounded-lg bg-surface/60 border border-border/60">
        <div className="flex-1">
          <div className="text-sm font-medium">Investigation Updates</div>
          <div className="text-xs text-muted-foreground mt-1">
            Receive notifications when investigations complete or fail
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

// ─── Settings page ────────────────────────────────────────────────────────────

function Settings() {
  return (
    <AppShell 
      title="Settings" 
      subtitle="Manage your profile, appearance, and notification preferences"
    >
      <div className="max-w-4xl space-y-6">
        <ProfileSection />
        <AppearanceSection />
        <NotificationsSection />
      </div>
    </AppShell>
  );
}
