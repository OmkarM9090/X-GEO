import { useRef, type ReactNode } from "react";
import { gsap, useGSAP, MOTION_OK } from "@/lib/gsap-config";
import { cn } from "@/lib/utils";

interface BlurRevealProps {
  children: ReactNode;
  className?: string;
  start?: string;
  duration?: number;
  blur?: number;
  y?: number;
}

/** Focuses a small content block as it enters the viewport. */
export function BlurReveal({
  children,
  className,
  start = "top 84%",
  duration = 0.8,
  blur = 10,
  y = 14,
}: BlurRevealProps) {
  const ref = useRef<HTMLDivElement>(null);

  useGSAP(
    () => {
      const element = ref.current;
      if (!element) return undefined;
      const media = gsap.matchMedia();
      media.add(MOTION_OK, () => {
        gsap.set(element, { willChange: "transform, opacity" });
        gsap.fromTo(
          element,
          { y, opacity: 0, filter: `blur(${blur}px)` },
          {
            y: 0,
            opacity: 1,
            filter: "blur(0px)",
            duration,
            ease: "power3.out",
            clearProps: "willChange,filter",
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
