import { Link } from "react-router-dom";
import type { LucideIcon } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface EmptyStateProps {
  Icon: LucideIcon;
  title: string;
  description: string;
  actionLabel?: string;
  actionTo?: string;
  /** Shows a "Coming in Phase 2" badge for shell pages. */
  phaseBadge?: boolean;
  className?: string;
}

/** Centered empty state — dashed frame, accent icon tile, optional CTA. */
export function EmptyState({
  Icon,
  title,
  description,
  actionLabel,
  actionTo,
  phaseBadge = false,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex min-h-[320px] flex-col items-center justify-center rounded-2xl border border-dashed border-border bg-card/40 px-6 py-14 text-center",
        className,
      )}
    >
      <span className="grid size-14 place-items-center rounded-2xl border border-accent/25 bg-accent/10 text-accent">
        <Icon className="size-6" strokeWidth={1.75} />
      </span>
      <h3 className="mt-6 font-heading text-h3 text-foreground">{title}</h3>
      <p className="mt-2 max-w-sm text-sm text-muted-foreground">{description}</p>
      <div className="mt-7 flex items-center gap-3">
        {actionLabel && actionTo && (
          <Button variant="accent" size="sm" asChild>
            <Link to={actionTo}>{actionLabel}</Link>
          </Button>
        )}
        {phaseBadge && <Badge variant="accent">Coming in Phase 2</Badge>}
      </div>
    </div>
  );
}
