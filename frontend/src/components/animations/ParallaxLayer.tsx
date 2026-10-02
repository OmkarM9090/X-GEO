import { useRef, type ReactNode } from "react";
import { gsap, useGSAP, MOTION_OK } from "@/lib/gsap-config";
import { cn } from "@/lib/utils";

interface ParallaxLayerProps {
  children: ReactNode;
  className?: string;
  speed?: number;
  start?: string;
  end?: string;
}

/** Transform-only parallax wrapper; rendered normally when motion is reduced. */
export function ParallaxLayer({
  children,
  className,
  speed = 12,
  start = "top bottom",
  end = "bottom top",
}: ParallaxLayerProps) {
  const ref = useRef<HTMLDivElement>(null);

  useGSAP(
    () => {
      const element = ref.current;
      if (!element) return undefined;
      const media = gsap.matchMedia();
      media.add(`${MOTION_OK} and (min-width: 768px)`, () => {
        const tween = gsap.fromTo(
          element,
          { yPercent: speed },
          {
            yPercent: -speed,
            ease: "none",
            scrollTrigger: { trigger: element, start, end, scrub: 1 },
          },
        );
        return () => tween.scrollTrigger?.kill();
      });
      return () => media.revert();
    },
    { scope: ref },
  );

  return <div ref={ref} className={cn("will-change-transform", className)}>{children}</div>;
}
