import { useRef, type ReactNode } from "react";
import { gsap, useGSAP, MOTION_OK } from "@/lib/gsap-config";
import { cn } from "@/lib/utils";

interface ClipRevealProps {
  children: ReactNode;
  className?: string;
  direction?: "left" | "right" | "up" | "down";
  start?: string;
  duration?: number;
}

/** Geometric reveal with a static fallback; reveal runs only once per mount. */
export function ClipReveal({
  children,
  className,
  direction = "left",
  start = "top 82%",
  duration = 0.9,
}: ClipRevealProps) {
  const ref = useRef<HTMLDivElement>(null);
  const hiddenClip = {
    left: "inset(0 100% 0 0)",
    right: "inset(0 0 0 100%)",
    up: "inset(100% 0 0 0)",
    down: "inset(0 0 100% 0)",
  }[direction];

  useGSAP(
    () => {
      const element = ref.current;
      if (!element) return undefined;
      const media = gsap.matchMedia();
      media.add(MOTION_OK, () => {
        gsap.fromTo(
          element,
          { clipPath: hiddenClip },
          {
            clipPath: "inset(0 0 0 0)",
            duration,
            ease: "power3.inOut",
            scrollTrigger: { trigger: element, start, once: true },
          },
        );
      });
      return () => media.revert();
    },
    { scope: ref },
  );

  return <div ref={ref} className={cn(className)}>{children}</div>;
}
