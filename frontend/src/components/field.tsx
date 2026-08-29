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
      <div className="text-[10px] uppercase font-mono tracking-widest text-muted-foreground">
        {label}
      </div>
      <div className={cn("mt-0.5 text-xs text-foreground", mono && "font-mono break-all")}>
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
        "rounded-sm border px-2.5 py-1 font-mono text-xs",
        tone === "success"
          ? "border-success/40 bg-success/10 text-success"
          : "border-border bg-surface-2 text-foreground",
      )}
    >
      <div className="text-[9px] uppercase tracking-widest text-muted-foreground">
        {label}
      </div>
      <div
        className={cn(
          "font-bold text-sm mt-0.5",
          tone === "success" && "text-success",
        )}
      >
        {value}
      </div>
    </div>
  );
}

