import { useEffect, useRef } from "react";
import type { ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";

interface ConfirmationModalProps {
  open: boolean;
  title: string;
  description?: ReactNode;
  confirmLabel?: string;
  cancelLabel?: string;
  destructive?: boolean;
  isPending?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmationModal({
  open,
  title,
  description,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  destructive = false,
  isPending = false,
  onConfirm,
  onCancel,
}: ConfirmationModalProps) {
  const cancelRef = useRef<HTMLButtonElement>(null);

  // Focus cancel on open for accessibility
  useEffect(() => {
    if (open) cancelRef.current?.focus();
  }, [open]);

  // Close on Escape
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onCancel();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open, onCancel]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-title"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onCancel}
        aria-hidden="true"
      />

      {/* Panel */}
      <div className="relative glass border border-border/60 rounded-2xl p-6 w-full max-w-md shadow-2xl animate-in fade-in zoom-in-95 duration-200">
        <div className="flex items-start gap-4">
          {destructive && (
            <div className="h-10 w-10 rounded-full bg-destructive/15 grid place-items-center shrink-0 mt-0.5">
              <AlertTriangle className="h-5 w-5 text-destructive" />
            </div>
          )}
          <div className="min-w-0 flex-1">
            <h2
              id="confirm-title"
              className="text-base font-semibold text-foreground"
            >
              {title}
            </h2>
            {description && (
              <p className="mt-1.5 text-sm text-muted-foreground">
                {description}
              </p>
            )}
          </div>
        </div>

        <div className="mt-6 flex justify-end gap-2">
          <Button
            ref={cancelRef}
            variant="ghost"
            onClick={onCancel}
            disabled={isPending}
          >
            {cancelLabel}
          </Button>
          <Button
            onClick={onConfirm}
            disabled={isPending}
            className={cn(
              "gap-2",
              destructive
                ? "bg-destructive text-destructive-foreground hover:bg-destructive/90"
                : "bg-gradient-to-r from-primary to-accent text-primary-foreground"
            )}
          >
            {isPending ? "Processing…" : confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}
