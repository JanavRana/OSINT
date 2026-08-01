/**
 * use-notifications.ts
 *
 * Polls listInvestigations() every 30 s, diffs against the previous snapshot,
 * and surfaces status changes as in-app notifications + sonner toasts.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { getDataProvider } from "@/lib/api/data-provider";
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

const POLL_INTERVAL_MS = 30_000;

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

  const addNotification = useCallback((notif: AppNotification) => {
    setNotifications((prev) => [notif, ...prev].slice(0, MAX_NOTIFS));

    // Toast with appropriate styling
    const toastFn =
      notif.severity === "critical"
        ? toast.error
        : notif.severity === "success"
        ? toast.success
        : toast.info;

    toastFn(notif.title, { description: notif.message });
  }, []);

  const poll = useCallback(async () => {
    try {
      const investigations = await getDataProvider().listInvestigations();
      const snapshot = snapshotRef.current;

      if (!initializedRef.current) {
        // Seed the snapshot on first run — don't fire notifications for existing state.
        for (const inv of investigations) {
          snapshot.set(inv.id, inv.status);
        }
        initializedRef.current = true;
        return;
      }

      // Check for status changes
      for (const inv of investigations) {
        const prevStatus = snapshot.get(inv.id);
        if (prevStatus === undefined) {
          // New investigation created (by someone else / another tab)
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
          addNotification(buildNotification(inv, prevStatus));
          snapshot.set(inv.id, inv.status);
        }
      }
    } catch {
      // Network errors during polling are silently swallowed
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
