import { useRef } from "react";
import { gsap, useGSAP, MOTION_OK } from "@/lib/gsap-config";
import { useMediaQuery } from "@/hooks/useMediaQuery";
import { useReducedMotion } from "@/hooks/useReducedMotion";

/** Desktop pointer accent: direct dot + lightly-lagged ring with delegated hover states. */
export function CustomCursor() {
  const dotRef = useRef<HTMLSpanElement>(null);
  const ringRef = useRef<HTMLSpanElement>(null);
  const finePointer = useMediaQuery("(hover: hover) and (pointer: fine) and (min-width: 768px)");
  const reducedMotion = useReducedMotion();
  const enabled = finePointer && !reducedMotion;

  useGSAP(
    () => {
      const dot = dotRef.current;
      const ring = ringRef.current;
      if (!enabled || !dot || !ring) return undefined;

      const media = gsap.matchMedia();
      media.add(MOTION_OK, () => {
        const dotX = gsap.quickTo(dot, "x", { duration: 0.01, ease: "none" });
        const dotY = gsap.quickTo(dot, "y", { duration: 0.01, ease: "none" });
        const ringX = gsap.quickTo(ring, "x", { duration: 0.15, ease: "power3.out" });
        const ringY = gsap.quickTo(ring, "y", { duration: 0.15, ease: "power3.out" });
        gsap.set([dot, ring], { xPercent: -50, yPercent: -50, x: 0, y: 0 });
        const scaleXTo = gsap.quickTo(ring, "scaleX", { duration: 0.2, ease: "power3.out" });
        const scaleYTo = gsap.quickTo(ring, "scaleY", { duration: 0.2, ease: "power3.out" });
        const onPointerMove = (event: PointerEvent) => {
          dotX(event.clientX);
          dotY(event.clientY);
          ringX(event.clientX);
          ringY(event.clientY);
          dot.classList.add("is-visible");
          ring.classList.add("is-visible");
        };
        const onPointerOver = (event: PointerEvent) => {
          const target = event.target;
          if (!(target instanceof Element)) return;
          const viewTarget = target.closest("[data-cursor='view'], [data-cursor-view], img, video");
          const interactiveTarget = target.closest(
            "a, button, [role='button'], [data-cursor='interactive'], article",
          );

          if (viewTarget) {
            ring.dataset.mode = "view";
            dot.classList.add("is-hidden");
            ring.classList.add("is-view");
            scaleXTo(1.9);
            scaleYTo(1);
          } else if (interactiveTarget) {
            ring.dataset.mode = "interactive";
            dot.classList.add("is-hidden");
            ring.classList.remove("is-view");
            scaleXTo(1.5);
            scaleYTo(1.5);
          } else {
            ring.dataset.mode = "default";
            dot.classList.remove("is-hidden");
            ring.classList.remove("is-view");
            scaleXTo(1);
            scaleYTo(1);
          }
        };
        const onWindowLeave = () => {
          dot.classList.remove("is-visible", "is-hidden");
          ring.classList.remove("is-visible", "is-view");
          ring.dataset.mode = "default";
          scaleXTo(1);
          scaleYTo(1);
        };

        document.documentElement.classList.add("has-custom-cursor");
        document.addEventListener("pointermove", onPointerMove, { passive: true });
        document.addEventListener("pointerover", onPointerOver, { passive: true });
        window.addEventListener("blur", onWindowLeave);
        document.documentElement.addEventListener("pointerleave", onWindowLeave);

        return () => {
          document.documentElement.classList.remove("has-custom-cursor");
          document.removeEventListener("pointermove", onPointerMove);
          document.removeEventListener("pointerover", onPointerOver);
          window.removeEventListener("blur", onWindowLeave);
          document.documentElement.removeEventListener("pointerleave", onWindowLeave);
          gsap.set([dot, ring], { clearProps: "transform" });
        };
      });

      return () => media.revert();
    },
    { scope: dotRef, dependencies: [enabled], revertOnUpdate: true },
  );

  if (!enabled) return null;

  return (
    <div aria-hidden="true" className="custom-cursor-root pointer-events-none fixed inset-0 z-[9999]">
      <span ref={dotRef} className="custom-cursor-dot" />
      <span ref={ringRef} className="custom-cursor-ring">
        <span className="custom-cursor-label">View</span>
      </span>
    </div>
  );
}
