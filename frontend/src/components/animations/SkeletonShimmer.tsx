import { useRef, type ReactNode } from "react";
import { gsap, useGSAP, MOTION_OK } from "@/lib/gsap-config";
import { cn } from "@/lib/utils";

interface SkeletonShimmerProps {
  loading: boolean;
  children?: ReactNode;
  skeleton?: ReactNode;
  className?: string;
  skeletonClassName?: string;
  /** Small delay used when a set of cards is revealed together. */
  index?: number;
  rounded?: string;
}

function DefaultSkeleton() {
  return (
    <div className="flex h-full min-h-40 flex-col justify-between p-5" aria-hidden="true">
      <div className="space-y-3">
        <div className="h-3 w-1/3 rounded-full bg-foreground/[0.07]" />
        <div className="h-7 w-2/3 rounded-md bg-foreground/[0.07]" />
      </div>
      <div className="grid grid-cols-3 gap-3">
        <div className="h-14 rounded-lg bg-foreground/[0.06]" />
        <div className="h-14 rounded-lg bg-foreground/[0.06]" />
        <div className="h-14 rounded-lg bg-foreground/[0.06]" />
      </div>
    </div>
  );
}

/** GPU-friendly card skeleton; the moving highlight is a transformed overlay, not background-position. */
export function SkeletonShimmer({
  loading,
  children,
  skeleton,
  className,
  skeletonClassName,
  index = 0,
  rounded = "rounded-2xl",
}: SkeletonShimmerProps) {
  const rootRef = useRef<HTMLDivElement>(null);

  useGSAP(
    () => {
      const root = rootRef.current;
      if (!root) return undefined;
      const skeletonLayer = root.querySelector<HTMLElement>("[data-skeleton-layer]");
      const contentLayer = root.querySelector<HTMLElement>("[data-loaded-content]");
      const sheen = root.querySelector<HTMLElement>("[data-skeleton-sheen]");
      if (!skeletonLayer || !sheen) return undefined;

      const media = gsap.matchMedia();
      media.add(MOTION_OK, () => {
        const delay = Math.max(0, index) * 0.1;
        if (loading) {
          gsap.set(skeletonLayer, { opacity: 1, willChange: "transform, opacity" });
          gsap.set(sheen, { xPercent: -160, opacity: 1, willChange: "transform, opacity" });
          gsap.to(sheen, {
            xPercent: 430,
            duration: 1.5,
            repeat: -1,
            ease: "none",
            delay,
          });
          if (contentLayer) {
            gsap.set(contentLayer, { opacity: 0, y: 10, pointerEvents: "none" });
          }
          return;
        }

        gsap.to(sheen, { opacity: 0, duration: 0.15, ease: "none" });
        gsap.to(skeletonLayer, {
          opacity: 0,
          duration: 0.2,
          delay,
          ease: "power1.out",
          clearProps: "willChange",
        });
        if (contentLayer) {
          gsap.fromTo(
            contentLayer,
            { opacity: 0, y: 10 },
            {
              opacity: 1,
              y: 0,
              duration: 0.3,
              delay,
              ease: "power3.out",
              clearProps: "willChange,transform,pointerEvents",
            },
          );
        }
      });

      media.add("(prefers-reduced-motion: reduce)", () => {
        gsap.set(skeletonLayer, { opacity: loading ? 1 : 0 });
        gsap.set(sheen, { opacity: 0 });
        if (contentLayer) gsap.set(contentLayer, { opacity: loading ? 0 : 1, y: 0 });
      });
      return () => media.revert();
    },
    { scope: rootRef, dependencies: [loading, index], revertOnUpdate: true },
  );

  return (
    <div
      ref={rootRef}
      className={cn("relative min-h-40 overflow-hidden border border-border bg-muted", rounded, className)}
      aria-busy={loading}
    >
      {(loading || children !== undefined) && (
        <div
          data-skeleton-layer
          className={cn("pointer-events-none absolute inset-0 z-10 overflow-hidden bg-muted", rounded, skeletonClassName)}
          aria-hidden="true"
        >
          {skeleton ?? <DefaultSkeleton />}
          <span
            data-skeleton-sheen
            className="pointer-events-none absolute inset-y-[-45%] left-[-25%] w-[36%] -skew-x-12 bg-gradient-to-r from-transparent via-foreground/[0.08] to-transparent opacity-0 will-change-transform"
          />
        </div>
      )}
      {children !== undefined && (
        <div data-loaded-content aria-hidden={loading} className="relative z-0">
          {children}
        </div>
      )}
    </div>
  );
}
