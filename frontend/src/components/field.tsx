import { cn } from "@/lib/utils";

export function Field({
  label,
  value,
  mono,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-widest text-muted-foreground">
        {label}
      </div>
      <div className={cn("mt-0.5", mono && "font-mono text-xs break-all")}>
        {value}
      </div>
    </div>
  );
}

export function MetricPill({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: "success";
}) {
  return (
    <div
      className={cn(
        "rounded-xl border px-3 py-1.5",
        tone === "success"
          ? "border-success/40 bg-success/10"
          : "border-border/60 bg-surface/60",
      )}
    >
      <div className="text-[10px] uppercase tracking-widest text-muted-foreground">
        {label}
      </div>
      <div
        className={cn(
          "text-sm font-display font-semibold",
          tone === "success" && "text-success",
        )}
      >
        {value}
      </div>
    </div>
  );
}
