import { cn } from "@/lib/utils";

/**
 * Subtle film-grain layer over the whole app. Pure SVG turbulence,
 * pointer-events:none, ~4% opacity — adds texture without banding.
 */
export function NoiseOverlay({ className }: { className?: string }) {
  return (
    <div
      aria-hidden="true"
      className={cn(
        "pointer-events-none fixed inset-0 z-[70] bg-noise opacity-[0.035] mix-blend-overlay dark:opacity-[0.05]",
        className,
      )}
    />
  );
}
