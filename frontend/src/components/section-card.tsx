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
    <Card className={cn("glass p-5 border-border/60", className)}>
      {(title || action) && (
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="font-display text-lg font-semibold">{title}</h3>
            {subtitle && (
              <p className="text-xs text-muted-foreground">{subtitle}</p>
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
      className="text-xs text-primary hover:underline flex items-center gap-1"
    >
      {children} <ArrowUpRight className="h-3 w-3" aria-hidden="true" />
    </Link>
  );
}
