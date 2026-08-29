import { Link } from "@tanstack/react-router";
import { ArrowUpRight } from "lucide-react";
import type { ReactNode } from "react";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export function SectionCard({
  title,
  subtitle,
  action,
  className,
  children,
}: {
  title: string;
  subtitle?: string;
  action?: ReactNode;
  className?: string;
  children: ReactNode;
}) {
  return (
    <Card className={cn("p-4 border-border bg-surface rounded-md", className)}>
      {(title || action) && (
        <div className="flex items-center justify-between pb-3 mb-3 border-b border-border/60">
          <div>
            <h3 className="font-display text-sm font-semibold text-foreground tracking-tight">{title}</h3>
            {subtitle && (
              <p className="text-[11px] text-muted-foreground mt-0.5">{subtitle}</p>
            )}
          </div>
          {action}
        </div>
      )}
      {children}
    </Card>
  );
}

export function ViewAllLink({ to, children = "View all" }: { to: string; children?: ReactNode }) {
  return (
    <Link
      to={to}
      className="text-xs text-primary hover:underline font-medium inline-flex items-center gap-1"
    >
      {children} <ArrowUpRight className="h-3 w-3" aria-hidden="true" />
    </Link>
  );
}

