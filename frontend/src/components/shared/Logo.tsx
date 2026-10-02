import { useId } from "react";
import { Link } from "react-router-dom";
import { cn } from "@/lib/utils";

/** X-GEO wordmark: gradient reticle "X" + tight-tracked Geist type. */
export function Logo({ className, to = "/" }: { className?: string; to?: string }) {
  const gradientId = useId();
  return (
    <Link
      to={to}
      aria-label="X-GEO — home"
      className={cn("group inline-flex items-center gap-2.5 outline-none", className)}
    >
      <span className="relative grid size-7 place-items-center">
        <svg viewBox="0 0 24 24" className="size-6" aria-hidden="true">
          <defs>
            <linearGradient id={gradientId} x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="hsl(var(--accent-glow))" />
              <stop offset="100%" stopColor="hsl(var(--accent))" />
            </linearGradient>
          </defs>
          <path
            d="M5.5 5.5l13 13M18.5 5.5l-13 13"
            stroke={`url(#${gradientId})`}
            strokeWidth="2.8"
            strokeLinecap="round"
          />
        </svg>
        <span className="absolute size-1.5 rounded-full bg-foreground transition-transform duration-300 group-hover:scale-125" />
      </span>
      <span className="font-heading text-[17px] font-semibold tracking-[-0.03em] text-foreground">
        X-GEO
      </span>
    </Link>
  );
}
