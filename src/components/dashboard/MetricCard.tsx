import type { LucideIcon } from "lucide-react";
import { TrendingDown, TrendingUp } from "lucide-react";
import { AnimatedCounter } from "@/components/shared/AnimatedCounter";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface MetricCardProps {
  label: string;
  Icon: LucideIcon;
  value: number;
  format?: "percent" | "number" | "raw";
  decimals?: number;
  suffix?: string;
  /** Signed delta; rendered as pp or plain count. */
  delta: number;
  deltaKind?: "points" | "count";
  hint?: string;
}

/** KPI card with GSAP-animated counter and signed delta chip. */
export function MetricCard({
  label,
  Icon,
  value,
  format = "number",
  decimals,
  suffix,
  delta,
  deltaKind = "points",
  hint,
}: MetricCardProps) {
  const positive = delta >= 0;
  const deltaText =
    deltaKind === "points"
      ? `${positive ? "+" : "−"}${Math.abs(delta * 100).toFixed(1)}pp`
      : `${positive ? "+" : "−"}${Math.abs(delta).toLocaleString()}`;

  return (
    <Card data-reveal className="p-6 transition-all duration-300 hover:-translate-y-0.5 hover:shadow-card">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">{label}</p>
        <span className="grid size-8 place-items-center rounded-lg border border-border bg-background/50 text-muted-foreground">
          <Icon className="size-4" strokeWidth={1.75} />
        </span>
      </div>
      <p className="mt-4 font-heading text-[34px] font-semibold leading-none tracking-[-0.02em] text-foreground">
        <AnimatedCounter value={value} format={format} decimals={decimals} suffix={suffix} />
      </p>
      <div className="mt-4 flex items-center gap-2">
        <span
          className={cn(
            "inline-flex items-center gap-1 rounded-full px-2 py-0.5 font-mono text-[11px] font-medium",
            positive ? "bg-success/10 text-success" : "bg-danger/10 text-danger",
          )}
        >
          {positive ? <TrendingUp className="size-3" /> : <TrendingDown className="size-3" />}
          {deltaText}
        </span>
        {hint && <span className="text-xs text-muted-foreground">{hint}</span>}
      </div>
    </Card>
  );
}
