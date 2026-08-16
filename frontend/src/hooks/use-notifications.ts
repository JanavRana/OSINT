/**
 * use-notifications.ts
 *
 * Polls listInvestigations() every 10 s, diffs against the previous snapshot,
 * and surfaces status changes as in-app notifications + sonner toasts.
 * Respects user notification preferences from settings.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { getDataProvider } from "@/lib/api/data-provider";
import { useNotificationPrefs } from "./use-settings";
import type { Investigation } from "@/types/domain";

export type NotifSeverity = "info" | "success" | "warning" | "critical";

export interface AppNotification {
  id: string;
  title: string;
  message: string;
  severity: NotifSeverity;
  timestamp: string;
  read: boolean;
  investigationId?: string;
}

const POLL_INTERVAL_MS = 10_000;

function statusSeverity(status: Investigation["status"]): NotifSeverity {
  switch (status) {
    case "failed": return "critical";
    case "completed": return "success";
    case "active": return "info";
    default: return "info";
  }
}

function buildNotification(inv: Investigation, oldStatus: string): AppNotification {
  const severity = statusSeverity(inv.status);
  const label = inv.status === "completed"
    ? "completed"
    : inv.status === "failed"
    ? "failed"
    : `changed to ${inv.status}`;

  return {
    id: `${inv.id}-${inv.status}-${Date.now()}`,
    title: `Investigation ${label}`,
    message: `${inv.name} changed from ${oldStatus} → ${inv.status}`,
    severity,
    timestamp: new Date().toISOString(),
    read: false,
    investigationId: inv.id,
  };
}

// Max notifications kept in memory
const MAX_NOTIFS = 50;

export function useNotifications() {
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const snapshotRef = useRef<Map<string, Investigation["status"]>>(new Map());
  const initializedRef = useRef(false);
  const { prefs } = useNotificationPrefs();

  const addNotification = useCallback((notif: AppNotification) => {
    console.log("[notifications] addNotification called:", {
      title: notif.title,
      prefs: prefs,
      investigationUpdates: prefs.investigationUpdates
    });

    // Check if investigation updates are enabled
    if (!prefs.investigationUpdates) {
      console.warn("[notifications] Investigation updates disabled - suppressing notification");
      return; // Don't add notification if disabled
    }

    setNotifications((prev) => [notif, ...prev].slice(0, MAX_NOTIFS));
    console.log("[notifications] Notification added to state");

    // Toast with appropriate styling based on severity and preferences
    const shouldShowToast = 
      (notif.severity === "critical" && prefs.criticalAlerts) ||
      (notif.severity !== "critical" && prefs.investigationUpdates);

    console.log("[notifications] shouldShowToast:", shouldShowToast, "severity:", notif.severity);

    if (shouldShowToast) {
      const toastFn =
        notif.severity === "critical"
          ? toast.error
          : notif.severity === "success"
          ? toast.success
          : toast.info;

      console.log("[notifications] Showing toast");
      toastFn(notif.title, { description: notif.message });
    }
  }, [prefs]);

  const poll = useCallback(async () => {
    try {
      const investigations = await getDataProvider().listInvestigations();
      const snapshot = snapshotRef.current;

      if (!initializedRef.current) {
        // Seed the snapshot on first run — don't fire notifications for existing state.
        console.log("[notifications] Initial poll - seeding snapshot with", investigations.length, "investigations");
        for (const inv of investigations) {
          console.log(`[notifications] Seeding ${inv.id}: ${inv.status}`);
          snapshot.set(inv.id, inv.status);
        }
        initializedRef.current = true;
        return;
      }

      // Check for status changes
      console.log("[notifications] Polling", investigations.length, "investigations");
      for (const inv of investigations) {
        const prevStatus = snapshot.get(inv.id);
        console.log(`[notifications] ${inv.id} (${inv.name}): ${prevStatus} → ${inv.status}`);
        if (prevStatus === undefined) {
          // New investigation created (by someone else / another tab)
          console.log(`[notifications] New investigation detected: ${inv.name}`);
          addNotification({
            id: `${inv.id}-new-${Date.now()}`,
            title: "New investigation created",
            message: `${inv.name} was created`,
            severity: "info",
            timestamp: new Date().toISOString(),
            read: false,
            investigationId: inv.id,
          });
          snapshot.set(inv.id, inv.status);
        } else if (prevStatus !== inv.status) {
          console.log(`[notifications] Status change detected: ${prevStatus} → ${inv.status}, creating notification`);
          addNotification(buildNotification(inv, prevStatus));
          snapshot.set(inv.id, inv.status);
        }
      }
    } catch (err) {
      // Network errors during polling are silently swallowed
      console.error("[notifications] Poll error:", err);
    }
  }, [addNotification]);

  useEffect(() => {
    // Immediate first poll
    poll();
    const interval = setInterval(poll, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [poll]);

  const markAllRead = useCallback(() => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  }, []);

  const markRead = useCallback((id: string) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, read: true } : n))
    );
  }, []);

  const unreadCount = notifications.filter((n) => !n.read).length;

  return { notifications, unreadCount, markAllRead, markRead };
}
