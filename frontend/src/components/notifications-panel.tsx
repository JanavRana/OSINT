/**
 * notifications-panel.tsx
 *
 * Bell icon with badge + popover notifications list.
 * Consumed by app-shell.tsx.
 */

import { useCallback } from "react";
import { Link } from "@tanstack/react-router";
import { Bell, CheckCheck, AlertTriangle, CheckCircle2, Info, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { cn } from "@/lib/utils";
import { fmtDate } from "@/lib/format";
import type { AppNotification, NotifSeverity } from "@/hooks/use-notifications";

const severityIcon: Record<NotifSeverity, typeof Info> = {
  info: Info,
  success: CheckCircle2,
  warning: AlertCircle,
  critical: AlertTriangle,
};

const severityColor: Record<NotifSeverity, string> = {
  info: "text-primary bg-primary/10 border-primary/30",
  success: "text-success bg-success/10 border-success/30",
  warning: "text-warning bg-warning/10 border-warning/30",
  critical: "text-destructive bg-destructive/10 border-destructive/30",
};

function NotificationItem({
  notif,
  onRead,
}: {
  notif: AppNotification;
  onRead: (id: string) => void;
}) {
  const Icon = severityIcon[notif.severity];
  return (
    <button
      className={cn(
        "w-full text-left flex items-start gap-2.5 px-3 py-2.5 hover:bg-surface-2 transition-colors font-mono text-xs border-b border-border/40",
        !notif.read && "bg-surface-2/60 border-l-2 border-l-primary"
      )}
      onClick={() => onRead(notif.id)}
      aria-label={notif.title}
    >
      <div
        className={cn(
          "h-6 w-6 rounded-sm border grid place-items-center shrink-0 mt-0.5",
          severityColor[notif.severity]
        )}
        aria-hidden="true"
      >
        <Icon className="h-3 w-3" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="text-xs font-bold text-foreground font-sans leading-snug">{notif.title}</div>
        <div className="text-[11px] text-muted-foreground mt-0.5 leading-snug line-clamp-2">
          {notif.message}
        </div>
        <time
          dateTime={notif.timestamp}
          className="text-[10px] text-muted-foreground mt-1 block font-mono"
        >
          {fmtDate(notif.timestamp)}
        </time>
      </div>
      {!notif.read && (
        <span className="h-1.5 w-1.5 rounded-full bg-primary shrink-0 mt-2" aria-label="Unread" />
      )}
    </button>
  );
}

export function NotificationsPanel({
  notifications,
  unreadCount,
  markAllRead,
  markRead,
}: {
  notifications: AppNotification[];
  unreadCount: number;
  markAllRead: () => void;
  markRead: (id: string) => void;
}) {
  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="relative h-8 w-8 text-muted-foreground hover:text-foreground"
          aria-label={`Notifications${unreadCount > 0 ? ` (${unreadCount} unread)` : ""}`}
        >
          <Bell className="h-4 w-4" />
          {unreadCount > 0 && (
            <span
              className="absolute top-1 right-1 min-w-[12px] h-3 rounded-sm bg-destructive text-[8px] font-mono font-bold text-destructive-foreground flex items-center justify-center px-0.5"
              aria-hidden="true"
            >
              {unreadCount > 9 ? "9+" : unreadCount}
            </span>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent
        align="end"
        className="w-80 p-0 bg-surface border-border shadow-2xl rounded-md font-mono text-xs"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-3 py-2 border-b border-border bg-surface-2/60">
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-foreground">System Audit Feed</h3>
            {unreadCount > 0 && (
              <p className="text-[10px] text-primary">{unreadCount} unread alerts</p>
            )}
          </div>
          {unreadCount > 0 && (
            <Button
              variant="ghost"
              size="sm"
              className="h-6 gap-1 text-[10px] font-mono"
              onClick={markAllRead}
            >
              <CheckCheck className="h-3 w-3" aria-hidden="true" />
              CLEAR
            </Button>
          )}
        </div>

        {/* Notifications list */}
        <div className="max-h-[380px] overflow-y-auto">
          {notifications.length === 0 ? (
            <div className="py-8 text-center">
              <Bell className="h-5 w-5 text-muted-foreground/40 mx-auto" />
              <p className="mt-2 text-xs font-mono text-muted-foreground">No alerts logged</p>
            </div>
          ) : (
            notifications.map((n) => (
              <NotificationItem key={n.id} notif={n} onRead={markRead} />
            ))
          )}
        </div>

        {/* Footer */}
        {notifications.length > 0 && (
          <div className="px-3 py-1.5 border-t border-border bg-surface-2/40 text-[10px]">
            <Link
              to="/dashboard"
              className="text-primary hover:underline font-bold"
              onClick={markAllRead}
            >
              COMMAND CENTER DASHBOARD →
            </Link>
          </div>
        )}
      </PopoverContent>
    </Popover>
  );
}

