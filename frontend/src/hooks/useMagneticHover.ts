import { useRef, type RefObject } from "react";
import { gsap, useGSAP, MOTION_OK } from "@/lib/gsap-config";

/** Pointer-fine magnetic translation with automatic useGSAP context cleanup. */
export function useMagneticHover<T extends HTMLElement = HTMLElement>(strength = 0.2): RefObject<T | null> {
  const ref = useRef<T>(null);

  useGSAP(
    () => {
      const element = ref.current;
      if (!element) return undefined;

      const media = gsap.matchMedia();
      media.add(`${MOTION_OK} and (hover: hover) and (pointer: fine)`, () => {
        const xTo = gsap.quickTo(element, "x", { duration: 0.32, ease: "power3.out" });
        const yTo = gsap.quickTo(element, "y", { duration: 0.32, ease: "power3.out" });
        const onPointerMove = (event: PointerEvent) => {
          const bounds = element.getBoundingClientRect();
          xTo((event.clientX - (bounds.left + bounds.width / 2)) * strength);
          yTo((event.clientY - (bounds.top + bounds.height / 2)) * strength);
        };
        const reset = () => {
          gsap.to(element, { x: 0, y: 0, duration: 0.55, ease: "elastic.out(1, 0.45)" });
        };

        element.addEventListener("pointermove", onPointerMove);
        element.addEventListener("pointerleave", reset);
        return () => {
          element.removeEventListener("pointermove", onPointerMove);
          element.removeEventListener("pointerleave", reset);
        };
      });

      return () => media.revert();
    },
    { scope: ref },
  );

  return ref;
}
