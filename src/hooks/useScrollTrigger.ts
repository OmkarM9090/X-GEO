import { useRef } from "react";
import { gsap, useGSAP, ScrollTrigger, MOTION_OK } from "@/lib/gsap";

interface RevealOptions {
  /** Selector scoped to the returned root ref. */
  selector?: string;
  y?: number;
  scale?: number;
  stagger?: number;
  start?: string;
  duration?: number;
}

/**
 * Batch reveal-on-scroll: children of the returned root matching
 * `selector` fade/rise (optionally scale) in when the root enters the
 * viewport. No-op under prefers-reduced-motion (content stays visible).
 */
export function useReveal<T extends HTMLElement = HTMLDivElement>(options: RevealOptions = {}) {
  const {
    selector = "[data-reveal]",
    y = 28,
    scale,
    stagger = 0.08,
    start = "top 82%",
    duration = 0.8,
  } = options;

  const ref = useRef<T>(null);

  useGSAP(
    () => {
      const root = ref.current;
      if (!root) return undefined;
      const targets = gsap.utils.toArray<HTMLElement>(root.querySelectorAll(selector));
      if (targets.length === 0) return undefined;

      const mm = gsap.matchMedia();
      mm.add(MOTION_OK, () => {
        gsap.set(targets, { willChange: "transform, opacity" });
        gsap.from(targets, {
          y,
          opacity: 0,
          ...(scale !== undefined ? { scale } : {}),
          duration,
          stagger,
          ease: "power3.out",
          clearProps: "willChange",
          scrollTrigger: { trigger: root, start, once: true },
        });
      });
      return () => mm.revert();
    },
    { scope: ref },
  );

  return ref;
}

/**
 * Scroll-scrubbed progress driver. Calls `onUpdate` with the
 * ScrollTrigger progress (0..1) of the returned section ref.
 * Reduced-motion users get the completed state immediately.
 */
export function useScrollProgress<T extends HTMLElement = HTMLElement>(
  onUpdate: (progress: number) => void,
  options: { start?: string; end?: string } = {},
) {
  const { start = "top 78%", end = "center 42%" } = options;
  const ref = useRef<T>(null);

  useGSAP(
    () => {
      const root = ref.current;
      if (!root) return undefined;

      const mm = gsap.matchMedia();
      mm.add(MOTION_OK, () => {
        const st = ScrollTrigger.create({
          trigger: root,
          start,
          end,
          scrub: 0.6,
          onUpdate: (self) => onUpdate(self.progress),
        });
        return () => st.kill();
      });
      mm.add("(prefers-reduced-motion: reduce)", () => {
        onUpdate(1);
        return undefined;
      });
      return () => mm.revert();
    },
    { scope: ref },
  );

  return ref;
}
