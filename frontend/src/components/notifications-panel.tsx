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
  info: "text-primary bg-primary/15",
  success: "text-success bg-success/15",
  warning: "text-warning bg-warning/15",
  critical: "text-destructive bg-destructive/15",
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
        "w-full text-left flex items-start gap-3 px-4 py-3 hover:bg-white/[0.04] transition-colors",
        !notif.read && "bg-primary/[0.04] border-l-2 border-primary"
      )}
      onClick={() => onRead(notif.id)}
      aria-label={notif.title}
    >
      <div
        className={cn(
          "h-7 w-7 rounded-md grid place-items-center shrink-0 mt-0.5",
          severityColor[notif.severity]
        )}
        aria-hidden="true"
      >
        <Icon className="h-3.5 w-3.5" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="text-xs font-medium text-foreground leading-snug">{notif.title}</div>
        <div className="text-[11px] text-muted-foreground mt-0.5 leading-snug line-clamp-2">
          {notif.message}
        </div>
        <time
          dateTime={notif.timestamp}
          className="text-[10px] text-muted-foreground/70 mt-1 block"
        >
          {fmtDate(notif.timestamp)}
        </time>
      </div>
      {!notif.read && (
        <span className="h-2 w-2 rounded-full bg-primary shrink-0 mt-2" aria-label="Unread" />
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
          className="relative"
          aria-label={`Notifications${unreadCount > 0 ? ` (${unreadCount} unread)` : ""}`}
        >
          <Bell className="h-4 w-4" />
          {unreadCount > 0 && (
            <span
              className="absolute top-1.5 right-1.5 min-w-[14px] h-3.5 rounded-full bg-destructive text-[9px] font-bold text-destructive-foreground flex items-center justify-center px-0.5"
              aria-hidden="true"
            >
              {unreadCount > 9 ? "9+" : unreadCount}
            </span>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent
        align="end"
        className="w-80 p-0 bg-sidebar/95 backdrop-blur-xl border-border/60 shadow-2xl"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-border/60">
          <div>
            <h3 className="text-sm font-semibold">Notifications</h3>
            {unreadCount > 0 && (
              <p className="text-[10px] text-muted-foreground">{unreadCount} unread</p>
            )}
          </div>
          {unreadCount > 0 && (
            <Button
              variant="ghost"
              size="sm"
              className="h-7 gap-1 text-xs"
              onClick={markAllRead}
            >
              <CheckCheck className="h-3 w-3" aria-hidden="true" />
              Mark all read
            </Button>
          )}
        </div>

        {/* Notifications list */}
        <div className="max-h-[420px] overflow-y-auto divide-y divide-border/40">
          {notifications.length === 0 ? (
            <div className="py-10 text-center">
              <Bell className="h-6 w-6 text-muted-foreground/40 mx-auto" />
              <p className="mt-2 text-xs text-muted-foreground">No notifications yet</p>
              <p className="text-[11px] text-muted-foreground/60 mt-1">
                Investigation status changes will appear here
              </p>
            </div>
          ) : (
            notifications.map((n) => (
              <NotificationItem key={n.id} notif={n} onRead={markRead} />
            ))
          )}
        </div>

        {/* Footer */}
        {notifications.length > 0 && (
          <div className="px-4 py-2 border-t border-border/60">
            <Link
              to="/dashboard"
              className="text-[11px] text-primary hover:underline"
              onClick={markAllRead}
            >
              View all in Dashboard →
            </Link>
          </div>
        )}
      </PopoverContent>
    </Popover>
  );
}
