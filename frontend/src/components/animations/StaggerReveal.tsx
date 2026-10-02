import { useRef, type ReactNode } from "react";
import { gsap, useGSAP, MOTION_OK } from "@/lib/gsap-config";
import { cn } from "@/lib/utils";

interface StaggerRevealProps {
  children: ReactNode;
  className?: string;
  selector?: string;
  stagger?: number;
  y?: number;
  scale?: number;
  start?: string;
  duration?: number;
}

/** Reveal a scoped group of children with a single, cleaned-up GSAP batch. */
export function StaggerReveal({
  children,
  className,
  selector = "[data-stagger-child]",
  stagger = 0.08,
  y = 22,
  scale,
  start = "top 84%",
  duration = 0.65,
}: StaggerRevealProps) {
  const ref = useRef<HTMLDivElement>(null);

  useGSAP(
    () => {
      const root = ref.current;
      if (!root) return undefined;
      const items = gsap.utils.toArray<HTMLElement>(root.querySelectorAll(selector));
      if (!items.length) return undefined;

      const media = gsap.matchMedia();
      media.add(MOTION_OK, () => {
        gsap.set(items, { willChange: "transform, opacity" });
        gsap.from(items, {
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
      return () => media.revert();
    },
    { scope: ref },
  );

  return <div ref={ref} className={cn(className)}>{children}</div>;
}
