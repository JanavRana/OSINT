// Reusable loading / empty / error states. Styled to match the existing UI —
// muted text, glass surfaces, no new layout language.
import type { ReactNode } from "react";
import { AlertTriangle, Inbox, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface BaseProps {
  className?: string;
  title?: string;
  description?: ReactNode;
}

export function LoadingState({
  className,
  title = "Loading…",
  description,
}: BaseProps) {
  return (
    <div
      role="status"
      aria-live="polite"
      aria-busy="true"
      className={cn(
        "flex flex-col items-center justify-center py-16 text-center text-muted-foreground",
        className,
      )}
    >
      <Loader2 className="h-5 w-5 animate-spin text-primary" aria-hidden="true" />
      <div className="mt-3 text-sm">{title}</div>
      {description && (
        <div className="mt-1 text-xs">{description}</div>
      )}
    </div>
  );
}

export function EmptyState({
  className,
  title = "Nothing to show yet",
  description,
  icon,
  action,
}: BaseProps & { icon?: ReactNode; action?: ReactNode }) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center py-16 text-center",
        className,
      )}
    >
      <div className="h-10 w-10 rounded-lg bg-white/5 grid place-items-center text-muted-foreground">
        {icon ?? <Inbox className="h-5 w-5" aria-hidden="true" />}
      </div>
      <div className="mt-3 text-sm text-foreground">{title}</div>
      {description && (
        <div className="mt-1 text-xs text-muted-foreground max-w-sm">
          {description}
        </div>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function ErrorState({
  className,
  title = "Something went wrong",
  description,
  onRetry,
}: BaseProps & { onRetry?: () => void }) {
  return (
    <Card
      role="alert"
      className={cn(
        "glass border-destructive/40 p-6 flex flex-col items-center text-center",
        className,
      )}
    >
      <AlertTriangle className="h-5 w-5 text-destructive" aria-hidden="true" />
      <div className="mt-2 text-sm font-medium">{title}</div>
      {description && (
        <div className="mt-1 text-xs text-muted-foreground">{description}</div>
      )}
      {onRetry && (
        <Button
          variant="secondary"
          size="sm"
          className="mt-4"
          onClick={onRetry}
        >
          Try again
        </Button>
      )}
    </Card>
  );
}

// Convenience: render the right state for an AsyncResource, otherwise
// hand back children. Keeps pages tidy without hiding data shape.
export function AsyncBoundary<T>({
  resource,
  loading,
  empty,
  isEmpty,
  errorTitle,
  children,
}: {
  resource: { data: T | undefined; isLoading: boolean; error: { message: string } | null; refetch?: () => void };
  loading?: ReactNode;
  empty?: ReactNode;
  isEmpty?: (data: T) => boolean;
  errorTitle?: string;
  children: (data: T) => ReactNode;
}) {
  if (resource.error) {
    return (
      <ErrorState
        title={errorTitle}
        description={resource.error.message}
        onRetry={resource.refetch}
      />
    );
  }
  if (resource.isLoading || resource.data === undefined) {
    return <>{loading ?? <LoadingState />}</>;
  }
  if (isEmpty && isEmpty(resource.data)) {
    return <>{empty ?? <EmptyState />}</>;
  }
  return <>{children(resource.data)}</>;
}
