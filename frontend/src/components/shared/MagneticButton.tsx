import { useRef, type ReactNode } from "react";
import { gsap, useGSAP, MOTION_OK } from "@/lib/gsap-config";
import { cn } from "@/lib/utils";

interface MagneticButtonProps {
  children: ReactNode;
  strength?: number;
  className?: string;
}

/** Subtle pointer-fine magnetic pull; disabled for touch and reduced-motion users. */
export function MagneticButton({ children, strength = 0.25, className }: MagneticButtonProps) {
  const outerRef = useRef<HTMLDivElement>(null);
  const innerRef = useRef<HTMLDivElement>(null);

  useGSAP(
    () => {
      const outer = outerRef.current;
      const inner = innerRef.current;
      if (!outer || !inner) return undefined;

      const media = gsap.matchMedia();
      media.add(`${MOTION_OK} and (hover: hover) and (pointer: fine)`, () => {
        const xTo = gsap.quickTo(inner, "x", { duration: 0.32, ease: "power3.out" });
        const yTo = gsap.quickTo(inner, "y", { duration: 0.32, ease: "power3.out" });
        const onPointerMove = (event: PointerEvent) => {
          const rect = outer.getBoundingClientRect();
          xTo((event.clientX - (rect.left + rect.width / 2)) * strength);
          yTo((event.clientY - (rect.top + rect.height / 2)) * strength);
        };
        const onPointerLeave = () => {
          gsap.to(inner, { x: 0, y: 0, duration: 0.55, ease: "elastic.out(1, 0.45)" });
        };

        outer.addEventListener("pointermove", onPointerMove);
        outer.addEventListener("pointerleave", onPointerLeave);
        return () => {
          outer.removeEventListener("pointermove", onPointerMove);
          outer.removeEventListener("pointerleave", onPointerLeave);
          gsap.set(inner, { clearProps: "transform" });
        };
      });
      return () => media.revert();
    },
    { scope: outerRef },
  );

  return (
    <div ref={outerRef} className={cn("-m-3 inline-block p-3", className)}>
      <div ref={innerRef} className="will-change-transform">{children}</div>
    </div>
  );
}
