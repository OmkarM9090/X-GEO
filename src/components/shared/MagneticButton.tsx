import { useRef, type ReactNode } from "react";
import { gsap, useGSAP } from "@/lib/gsap";
import { cn } from "@/lib/utils";

interface MagneticButtonProps {
  children: ReactNode;
  /** Translation factor relative to cursor offset (spec: 0.3). */
  strength?: number;
  className?: string;
}

/**
 * Magnetic hover: the padded hit area pulls its content toward the cursor
 * by (dx, dy) × strength while within ~100px, then springs back with an
 * elastic ease on leave. Pointer-only — inert on touch devices.
 */
export function MagneticButton({ children, strength = 0.3, className }: MagneticButtonProps) {
  const outerRef = useRef<HTMLDivElement>(null);
  const innerRef = useRef<HTMLDivElement>(null);

  useGSAP(
    () => {
      const outer = outerRef.current;
      const inner = innerRef.current;
      if (!outer || !inner) return undefined;
      if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return undefined;
      if (!window.matchMedia("(pointer: fine)").matches) return undefined;

      const xTo = gsap.quickTo(inner, "x", { duration: 0.35, ease: "power3.out" });
      const yTo = gsap.quickTo(inner, "y", { duration: 0.35, ease: "power3.out" });

      const onMove = (event: MouseEvent) => {
        const rect = outer.getBoundingClientRect();
        const dx = event.clientX - (rect.left + rect.width / 2);
        const dy = event.clientY - (rect.top + rect.height / 2);
        xTo(dx * strength);
        yTo(dy * strength);
      };
      const onLeave = () => {
        gsap.to(inner, { x: 0, y: 0, duration: 0.8, ease: "elastic.out(1, 0.35)" });
      };

      outer.addEventListener("mousemove", onMove);
      outer.addEventListener("mouseleave", onLeave);
      return () => {
        outer.removeEventListener("mousemove", onMove);
        outer.removeEventListener("mouseleave", onLeave);
      };
    },
    { scope: outerRef },
  );

  return (
    <div ref={outerRef} className={cn("inline-block p-3 -m-3", className)}>
      <div ref={innerRef} className="will-change-transform">
        {children}
      </div>
    </div>
  );
}
