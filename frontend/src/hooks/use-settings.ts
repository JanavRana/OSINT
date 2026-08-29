/**
 * use-settings.ts
 *
 * Provides typed localStorage persistence for all user settings:
 * profile, notifications, theme, and connector preferences.
 * Each section is independently stored and loaded.
 */

import { useCallback, useEffect, useState } from "react";

// ─── Profile ────────────────────────────────────────────────────────────────

export interface ProfileSettings {
  fullName: string;
  role: string;
  email: string;
  clearance: string;
  initials: string;
}

const PROFILE_DEFAULT: ProfileSettings = {
  fullName: "Analyst",
  role: "Intelligence Analyst",
  email: "analyst@intelweave.io",
  clearance: "TLP:AMBER",
  initials: "AI",
};

// ─── Notifications ──────────────────────────────────────────────────────────

export interface NotificationPrefs {
  criticalAlerts: boolean;
  connectorFailures: boolean;
  investigationUpdates: boolean;
  weeklyDigest: boolean;
}

const NOTIF_DEFAULT: NotificationPrefs = {
  criticalAlerts: true,
  connectorFailures: true,
  investigationUpdates: true,
  weeklyDigest: false,
};

// ─── Theme ──────────────────────────────────────────────────────────────────

export interface ThemeSettings {
  preset: string; // preset name
  mode: "light" | "dark"; // theme mode
  primaryColor?: string; // CSS color value for primary
  accentColor?: string; // CSS color value for accent
}

const THEME_DEFAULT: ThemeSettings = { 
  preset: "Cyan · Violet",
  mode: "dark",
  primaryColor: "oklch(0.82 0.17 195)",
  accentColor: "oklch(0.65 0.24 295)",
};

// ─── Connector Prefs ────────────────────────────────────────────────────────

export type ConnectorPrefs = Record<string, boolean>; // connectorId → enabled

// ─── Generic storage helper ─────────────────────────────────────────────────

function readStorage<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return fallback;
    return { ...fallback, ...(JSON.parse(raw) as Partial<T>) };
  } catch {
    return fallback;
  }
}

function writeStorage<T>(key: string, value: T): void {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Quota exceeded or private mode — silently ignore.
  }
}

// ─── Hooks ──────────────────────────────────────────────────────────────────

export function useProfileSettings() {
  const [profile, setProfileState] = useState<ProfileSettings>(() =>
    readStorage("axiom_profile", PROFILE_DEFAULT)
  );

  const saveProfile = useCallback((next: ProfileSettings) => {
    writeStorage("axiom_profile", next);
    setProfileState(next);
  }, []);

  return { profile, saveProfile };
}

export function useNotificationPrefs() {
  const [prefs, setPrefsState] = useState<NotificationPrefs>(() => {
    const stored = readStorage("axiom_notifications", NOTIF_DEFAULT);
    console.log("[settings] Loaded notification prefs:", stored);
    return stored;
  });

  const toggle = useCallback((key: keyof NotificationPrefs) => {
    setPrefsState((prev) => {
      const next = { ...prev, [key]: !prev[key] };
      console.log("[settings] Toggling", key, ":", prev[key], "→", next[key]);
      writeStorage("axiom_notifications", next);
      return next;
    });
  }, []);

  return { prefs, toggle };
}

export function useThemeSettings() {
  const [theme, setThemeState] = useState<ThemeSettings>(() =>
    readStorage("axiom_theme", THEME_DEFAULT)
  );

  // Apply theme to document on mount and when theme changes
  useEffect(() => {
    const root = document.documentElement;
    
    // Apply mode
    if (theme.mode === "light") {
      root.classList.add("light");
      root.classList.remove("dark");
    } else {
      root.classList.add("dark");
      root.classList.remove("light");
    }

    // Apply color variables if they exist
    if (theme.primaryColor) {
      root.style.setProperty("--primary", theme.primaryColor);
      root.style.setProperty("--sidebar-primary", theme.primaryColor);
      root.style.setProperty("--ring", theme.primaryColor);
      root.style.setProperty("--sidebar-ring", theme.primaryColor);
      root.style.setProperty("--cyan", theme.primaryColor);
    }
    if (theme.accentColor) {
      root.style.setProperty("--accent", theme.accentColor);
      root.style.setProperty("--violet", theme.accentColor);
    }
  }, [theme]);

  const setPreset = useCallback((preset: string, primaryColor: string, accentColor: string) => {
    const next = { ...theme, preset, primaryColor, accentColor };
    writeStorage("axiom_theme", next);
    setThemeState(next);
  }, [theme]);

  const setMode = useCallback((mode: "light" | "dark") => {
    const next = { ...theme, mode };
    writeStorage("axiom_theme", next);
    setThemeState(next);
  }, [theme]);

  return { theme, setPreset, mode: theme.mode, setMode };
}

export function useConnectorPrefs() {
  const [connectorPrefs, setConnectorPrefs] = useState<ConnectorPrefs>(() => {
    try {
      const raw = localStorage.getItem("axiom_connector_prefs");
      return raw ? (JSON.parse(raw) as ConnectorPrefs) : {};
    } catch {
      return {};
    }
  });

  const setConnectorEnabled = useCallback((id: string, enabled: boolean) => {
    setConnectorPrefs((prev) => {
      const next = { ...prev, [id]: enabled };
      writeStorage("axiom_connector_prefs", next);
      return next;
    });
  }, []);

  const isEnabled = useCallback(
    (id: string, defaultValue = true) =>
      connectorPrefs[id] !== undefined ? connectorPrefs[id] : defaultValue,
    [connectorPrefs]
  );

  return { isEnabled, setConnectorEnabled };
}

// ─── Session report store ───────────────────────────────────────────────────

export interface SessionReport {
  reportId: string;
  investigationId: string;
  investigationName: string;
  status: "queued" | "generating" | "ready" | "failed";
  createdAt: string;
}

const SESSION_KEY = "axiom_reports";

function readSessionReports(): SessionReport[] {
  try {
    const raw = sessionStorage.getItem(SESSION_KEY);
    return raw ? (JSON.parse(raw) as SessionReport[]) : [];
  } catch {
    return [];
  }
}

function writeSessionReports(reports: SessionReport[]): void {
  try {
    sessionStorage.setItem(SESSION_KEY, JSON.stringify(reports));
  } catch {
    // ignore
  }
}

export function useSessionReports() {
  const [reports, setReports] = useState<SessionReport[]>(() =>
    readSessionReports()
  );

  // Sync across tabs / components in same session
  useEffect(() => {
    const handler = () => setReports(readSessionReports());
    window.addEventListener("storage", handler);
    return () => window.removeEventListener("storage", handler);
  }, []);

  const addReport = useCallback((report: SessionReport) => {
    setReports((prev) => {
      const next = [report, ...prev.filter((r) => r.reportId !== report.reportId)];
      writeSessionReports(next);
      return next;
    });
  }, []);

  const updateReport = useCallback((reportId: string, updates: Partial<SessionReport>) => {
    setReports((prev) => {
      const next = prev.map((r) => (r.reportId === reportId ? { ...r, ...updates } : r));
      writeSessionReports(next);
      return next;
    });
  }, []);

  return { reports, addReport, updateReport };
}
