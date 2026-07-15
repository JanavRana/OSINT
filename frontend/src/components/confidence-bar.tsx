import { cn } from "@/lib/utils";

interface ConfidenceBarProps {
  value: number;
  className?: string;
  showValue?: boolean;
  valueWidthClass?: string;
  ariaLabel?: string;
}

function toneFor(value: number) {
  if (value >= 85) return "bg-success";
  if (value >= 65) return "bg-warning";
  return "bg-destructive";
}

export function ConfidenceBar({
  value,
  className,
  showValue = true,
  valueWidthClass = "w-8",
  ariaLabel = "Confidence",
}: ConfidenceBarProps) {
  const clamped = Math.max(0, Math.min(100, value));
  return (
    <div className={cn("flex items-center gap-2", className)}>
      <div
        className="h-1.5 flex-1 rounded-full bg-white/5 overflow-hidden"
        role="progressbar"
        aria-label={ariaLabel}
        aria-valuenow={clamped}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className={cn("h-full", toneFor(clamped))}
          style={{ width: `${clamped}%` }}
        />
      </div>
      {showValue && (
        <span className={cn("text-xs font-mono text-right", valueWidthClass)}>
          {clamped}%
        </span>
      )}
    </div>
  );
}
