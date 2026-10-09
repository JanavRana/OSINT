import { Link, useRouterState } from "@tanstack/react-router";
import type { ReactNode } from "react";
import {
  LayoutDashboard, Search, Network, UserSearch, Clock, FileText,
  Settings, Plus, Terminal, Shield, LogOut, ChevronDown
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Toaster } from "sonner";
import { cn } from "@/lib/utils";
import { useNotifications } from "@/hooks/use-notifications";
import { useProfileSettings } from "@/hooks/use-settings";
import { NotificationsPanel } from "@/components/notifications-panel";
import { useConnectors } from "@/hooks/use-osint-data";
import { useLogout, useCurrentUser } from "@/hooks/use-auth";
import { GlobalSearch } from "@/components/global-search";

const nav = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/investigations", label: "Investigations", icon: Search },
  { to: "/graph", label: "Graph View", icon: Network },
  { to: "/identity", label: "Identity Profile", icon: UserSearch },
  { to: "/timeline", label: "Timeline", icon: Clock },
  { to: "/reports", label: "Reports", icon: FileText },
  { to: "/settings", label: "Settings", icon: Settings },
];

function ConnectorStatusSidebar() {
  const connectorsRes = useConnectors(undefined);
  const connectors = connectorsRes.data ?? [];

  const online = connectors.filter((c) => c.status === "success").length;
  const total = connectors.length;

  const display = total === 0 ? "No runs yet" : `${online}/${total} connectors ok`;
  const pct = total === 0 ? 0 : Math.round((online / total) * 100);

  const healthColor = total === 0 ? "text-muted-foreground" : pct === 100 ? "text-success" : pct > 50 ? "text-warning" : "text-destructive";
  const barColor = pct === 100 ? "oklch(0.70 0.18 148)" : pct > 50 ? "oklch(0.76 0.16 78)" : "oklch(0.60 0.22 25)";

  return (
    <div className="rounded-md border border-border/60 bg-surface-2/60 p-2.5 text-xs font-mono backdrop-blur-sm">
      <div className="flex items-center gap-2">
        <Shield className="h-3 w-3 text-primary shrink-0" />
        <span className="text-muted-foreground/80 uppercase tracking-widest text-[9px]">Sys Health</span>
        <span className={cn("ml-auto text-[10px] font-bold tabular-nums", healthColor)}>
          {total === 0 ? "READY" : `${pct}%`}
        </span>
      </div>
      <div className="mt-2 h-px rounded-full overflow-hidden" style={{ background: "oklch(1 0 0 / 0.06)" }}>
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{
            width: `${pct || 0}%`,
            background: total === 0 ? "oklch(0.68 0.18 230)" : barColor,
            boxShadow: pct > 0 ? `0 0 6px ${barColor}` : "none",
          }}
        />
      </div>
      <div className="mt-1.5 text-[9px] text-muted-foreground/60 flex justify-between">
        <span>{display}</span>
        <span className="text-success/70">● ONLINE</span>
      </div>
    </div>
  );
}

export function AppShell({ children, title, subtitle, actions }: {
  children: ReactNode; title?: string; subtitle?: ReactNode; actions?: ReactNode;
}) {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const { notifications, unreadCount, markAllRead, markRead } = useNotifications();
  const { profile } = useProfileSettings();

  const initials = profile.initials ||
    profile.fullName
      .split(" ")
      .map((n) => n[0])
      .slice(0, 2)
      .join("")
      .toUpperCase() || "AI";

  const logout = useLogout();
  const authUser = useCurrentUser();
  const displayName = authUser?.fullName || profile.fullName;
  const displayInitials = authUser
    ? authUser.fullName.split(" ").map((n) => n[0]).slice(0, 2).join("").toUpperCase() || "AI"
    : initials;
  const displayRole = authUser?.email || profile.role;

  return (
    <div className="min-h-screen w-full flex bg-background text-foreground text-sm">
      {/* Sonner toast container */}
      <Toaster richColors position="top-right" />

      {/* Sidebar */}
      <aside className="hidden md:flex w-56 shrink-0 flex-col border-r border-sidebar-border bg-sidebar">
        {/* Brand header */}
        <div className="flex items-center gap-2.5 px-4 h-13 border-b border-sidebar-border">
          <div
            className="h-7 w-7 rounded-md grid place-items-center shrink-0 text-primary-foreground font-mono font-bold text-xs"
            style={{
              background: "linear-gradient(135deg, oklch(0.68 0.18 230) 0%, oklch(0.60 0.22 255) 100%)",
              boxShadow: "0 0 12px oklch(0.68 0.18 230 / 0.4)",
            }}
          >
            <Terminal className="h-4 w-4" />
          </div>
          <div className="flex flex-col leading-none">
            <span className="font-mono text-xs font-bold tracking-tight uppercase text-sidebar-foreground">INTELWEAVE</span>
            <span className="text-[9px] font-mono tracking-widest text-muted-foreground/70 uppercase mt-0.5">OSINT Console</span>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-2 space-y-0.5">
          <div className="px-2.5 py-2 text-[9px] font-mono uppercase tracking-widest text-muted-foreground/50">
            Workspace
          </div>
          {nav.map((n) => {
            const active = pathname === n.to || (n.to !== "/dashboard" && pathname.startsWith(n.to));
            const Icon = n.icon;
            return (
              <Link
                key={n.to}
                to={n.to}
                className={cn(
                  "group flex items-center gap-2.5 rounded-md px-2.5 py-1.5 text-xs transition-all duration-200 font-medium",
                  active
                    ? "bg-primary/12 text-primary font-semibold"
                    : "text-muted-foreground/80 hover:text-sidebar-foreground hover:bg-sidebar-accent"
                )}
                style={active ? {
                  boxShadow: "inset 3px 0 0 oklch(0.68 0.18 230)",
                } : undefined}
              >
                <Icon
                  className={cn(
                    "h-3.5 w-3.5 shrink-0 transition-all duration-200",
                    active ? "text-primary" : "text-muted-foreground/60 group-hover:text-sidebar-foreground",
                  )}
                />
                <span className="truncate">{n.label}</span>
                {active && (
                  <span
                    className="ml-auto h-1.5 w-1.5 rounded-full shrink-0 animate-pulse-dot"
                    style={{ background: "oklch(0.68 0.18 230)" }}
                    aria-hidden="true"
                  />
                )}
              </Link>
            );
          })}
        </nav>

        {/* Footer connector status */}
        <div className="p-2 border-t border-border">
          <ConnectorStatusSidebar />
        </div>
      </aside>

      {/* Main Container */}
      <div className="flex-1 min-w-0 flex flex-col">
        {/* Topbar */}
        <header
          className="h-13 border-b border-border px-4 flex items-center gap-3 sticky top-0 z-30 backdrop-blur-md"
          style={{ background: "color-mix(in oklch, var(--color-surface) 88%, transparent)" }}
        >
          <GlobalSearch />
          <div className="ml-auto flex items-center gap-2">
            <NotificationsPanel
              notifications={notifications}
              unreadCount={unreadCount}
              markAllRead={markAllRead}
              markRead={markRead}
            />
            <Link to="/investigations/new">
              <Button size="sm" className="h-8 gap-1.5 text-xs font-medium bg-primary text-primary-foreground hover:bg-primary/90 rounded-sm">
                <Plus className="h-3.5 w-3.5" /> New Case
              </Button>
            </Link>
            <div className="hidden sm:flex items-center gap-2 pl-2 border-l border-border ml-1">
              <div className="h-7 w-7 rounded-sm bg-surface-3 border border-border grid place-items-center text-xs font-mono font-bold text-foreground">
                {displayInitials}
              </div>
              <div className="hidden lg:block leading-none">
                <div className="text-xs font-medium text-foreground">{displayName}</div>
                <div className="text-[10px] font-mono text-muted-foreground mt-0.5">{displayRole}</div>
              </div>
            </div>
            <Button
              variant="ghost"
              size="icon"
              title="Sign out"
              onClick={logout}
              className="h-8 w-8 text-muted-foreground hover:text-foreground hidden sm:flex"
            >
              <LogOut className="h-3.5 w-3.5" />
            </Button>
          </div>
        </header>

        {/* Page title / actions bar */}
        {(title || actions) && (
          <div className="px-4 md:px-6 py-3 border-b border-border/60 bg-surface/30 flex flex-wrap items-center justify-between gap-3">
            <div className="min-w-0">
              {title && <h1 className="text-base font-semibold tracking-tight text-foreground font-display flex items-center gap-2">{title}</h1>}
              {subtitle && <p className="text-xs text-muted-foreground mt-0.5">{subtitle}</p>}
            </div>
            {actions && <div className="flex items-center gap-2">{actions}</div>}
          </div>
        )}

        <main className="flex-1 min-w-0 px-4 md:px-6 py-4">{children}</main>
      </div>
    </div>
  );
}

