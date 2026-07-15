import { Link, useRouterState } from "@tanstack/react-router";
import type { ReactNode } from "react";
import {
  LayoutDashboard, Search, Network, UserSearch, Clock, FileText,
  Settings, Bell, Command, Plus, Radar, Shield, LogOut, ChevronDown
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

const nav = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/investigations", label: "Investigations", icon: Search },
  { to: "/graph", label: "Graph View", icon: Network },
  { to: "/identity", label: "Identity Profile", icon: UserSearch },
  { to: "/timeline", label: "Timeline", icon: Clock },
  { to: "/reports", label: "Reports", icon: FileText },
  { to: "/settings", label: "Settings", icon: Settings },
];

export function AppShell({ children, title, subtitle, actions }: {
  children: ReactNode; title?: string; subtitle?: ReactNode; actions?: ReactNode;
}) {
  const pathname = useRouterState({ select: (s) => s.location.pathname });

  return (
    <div className="min-h-screen w-full flex bg-background text-foreground">
      {/* Sidebar */}
      <aside className="hidden md:flex w-64 shrink-0 flex-col border-r border-border/60 bg-sidebar/70 backdrop-blur-xl">
        <div className="flex items-center gap-2 px-5 h-16 border-b border-border/60">
          <div className="relative">
            <div className="absolute inset-0 rounded-lg blur-md opacity-70 bg-primary/50" />
            <div className="relative h-9 w-9 rounded-lg grid place-items-center bg-gradient-to-br from-primary to-accent">
              <Radar className="h-5 w-5 text-primary-foreground" strokeWidth={2.5} />
            </div>
          </div>
          <div className="flex flex-col leading-tight">
            <span className="font-display font-bold tracking-tight">AXIOM</span>
            <span className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">OSINT Intel</span>
          </div>
        </div>
        <nav className="flex-1 p-3 space-y-1">
          {nav.map((n) => {
            const active = pathname === n.to || (n.to !== "/dashboard" && pathname.startsWith(n.to));
            const Icon = n.icon;
            return (
              <Link
                key={n.to}
                to={n.to}
                className={cn(
                  "group flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-all",
                  active
                    ? "bg-gradient-to-r from-primary/15 to-accent/10 text-foreground shadow-[inset_0_0_0_1px] shadow-primary/20"
                    : "text-muted-foreground hover:text-foreground hover:bg-white/5"
                )}
              >
                <Icon className={cn("h-4 w-4 shrink-0", active && "text-primary")} />
                <span className="truncate">{n.label}</span>
                {active && <span className="ml-auto h-1.5 w-1.5 rounded-full bg-primary pulse-ring" />}
              </Link>
            );
          })}
        </nav>
        <div className="p-3 border-t border-border/60">
          <div className="glass rounded-xl p-3">
            <div className="flex items-center gap-2 text-xs">
              <Shield className="h-3.5 w-3.5 text-primary" />
              <span className="text-muted-foreground">System status</span>
              <span className="ml-auto text-success font-medium">Operational</span>
            </div>
            <div className="mt-2 h-1.5 rounded-full bg-white/5 overflow-hidden">
              <div className="h-full w-[86%] bg-gradient-to-r from-primary to-accent" />
            </div>
            <div className="mt-1.5 text-[10px] text-muted-foreground">38 / 42 connectors online</div>
          </div>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 min-w-0 flex flex-col">
        {/* Topbar */}
        <header className="h-16 border-b border-border/60 bg-background/60 backdrop-blur-xl px-4 md:px-6 flex items-center gap-3 sticky top-0 z-30">
          <div className="relative flex-1 max-w-xl">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search identifiers, investigations, wallets, domains…"
              className="pl-9 pr-16 h-10 bg-surface/60 border-border/60 focus-visible:ring-primary/40"
            />
            <kbd className="absolute right-2 top-1/2 -translate-y-1/2 h-6 px-1.5 rounded-md border border-border/70 bg-surface text-[10px] font-mono text-muted-foreground flex items-center gap-1">
              <Command className="h-3 w-3" />K
            </kbd>
          </div>
          <div className="ml-auto flex items-center gap-2">
            <Button variant="ghost" size="icon" className="relative">
              <Bell className="h-4 w-4" />
              <span className="absolute top-2 right-2 h-1.5 w-1.5 rounded-full bg-destructive" />
            </Button>
            <Link to="/investigations/new">
              <Button className="bg-gradient-to-r from-primary to-accent text-primary-foreground hover:opacity-90 gap-2 shadow-[0_0_20px_-6px_var(--primary)]">
                <Plus className="h-4 w-4" /> New Investigation
              </Button>
            </Link>
            <div className="hidden sm:flex items-center gap-2 pl-2 ml-2 border-l border-border/60">
              <div className="h-8 w-8 rounded-full bg-gradient-to-br from-primary/70 to-accent/70 grid place-items-center text-xs font-bold text-primary-foreground">
                MC
              </div>
              <div className="hidden lg:block leading-tight">
                <div className="text-xs font-medium">M. Chen</div>
                <div className="text-[10px] text-muted-foreground">Sr. Analyst</div>
              </div>
              <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
            </div>
            <Link to="/auth" className="hidden sm:block">
              <Button variant="ghost" size="icon" title="Sign out">
                <LogOut className="h-4 w-4" />
              </Button>
            </Link>
          </div>
        </header>

        {/* Page header */}
        {(title || actions) && (
          <div className="px-4 md:px-8 pt-6 pb-2 flex flex-wrap items-end gap-4">
            <div className="min-w-0">
              {title && <h1 className="text-2xl md:text-3xl font-semibold tracking-tight">{title}</h1>}
              {subtitle && <p className="text-sm text-muted-foreground mt-1">{subtitle}</p>}
            </div>
            {actions && <div className="ml-auto flex items-center gap-2">{actions}</div>}
          </div>
        )}

        <main className="flex-1 min-w-0 px-4 md:px-8 py-6">{children}</main>
      </div>
    </div>
  );
}
