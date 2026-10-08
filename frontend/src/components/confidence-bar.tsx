import { cn } from "@/lib/utils";

interface ConfidenceBarProps {
  value: number;
  className?: string;
  showValue?: boolean;
  valueWidthClass?: string;
  ariaLabel?: string;
}

export function formatConfidencePercent(value: number): number {
  const pct = value <= 1 ? value * 100 : value;
  return Math.round(pct);
}

function gradientFor(value: number): string {
  if (value >= 85)
    return "linear-gradient(90deg, oklch(0.70 0.18 148), oklch(0.75 0.16 160))";
  if (value >= 65)
    return "linear-gradient(90deg, oklch(0.76 0.16 78), oklch(0.80 0.14 90))";
  return "linear-gradient(90deg, oklch(0.60 0.22 25), oklch(0.65 0.18 35))";
}

function shadowFor(value: number): string {
  if (value >= 85) return "0 0 6px oklch(0.70 0.18 148 / 0.60)";
  if (value >= 65) return "0 0 6px oklch(0.76 0.16 78 / 0.55)";
  return "0 0 6px oklch(0.60 0.22 25 / 0.55)";
}

function labelColorFor(value: number): string {
  if (value >= 85) return "text-success";
  if (value >= 65) return "text-warning";
  return "text-destructive";
}

export function ConfidenceBar({
  value,
  className,
  showValue = true,
  valueWidthClass = "w-8",
  ariaLabel = "Confidence",
}: ConfidenceBarProps) {
  const percentValue = formatConfidencePercent(value);
  const clamped = Math.max(0, Math.min(100, percentValue));

  return (
    <div className={cn("flex items-center gap-2", className)}>
      <div
        className="h-1.5 flex-1 rounded-full overflow-hidden"
        style={{ background: "oklch(1 0 0 / 0.05)" }}
        role="progressbar"
        aria-label={ariaLabel}
        aria-valuenow={clamped}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className="h-full rounded-full transition-all duration-700 ease-out"
          style={{
            width: `${clamped}%`,
            background: gradientFor(clamped),
            boxShadow: clamped > 20 ? shadowFor(clamped) : "none",
          }}
        />
      </div>
      {showValue && (
        <span
          className={cn(
            "text-[11px] font-mono font-semibold text-right shrink-0",
            valueWidthClass,
            labelColorFor(clamped),
          )}
        >
          {clamped}%
        </span>
      )}
    </div>
  );
}
