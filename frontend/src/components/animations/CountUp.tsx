import { useRef } from "react";
import { gsap, useGSAP, ScrollTrigger, MOTION_OK } from "@/lib/gsap-config";
import { cn } from "@/lib/utils";

interface CountUpProps {
  to: number;
  from?: number;
  prefix?: string;
  suffix?: string;
  decimals?: number;
  duration?: number;
  trigger?: "scroll" | "load";
  className?: string;
}

/** Digit counter that updates one text node and cleans up its ScrollTrigger. */
export function CountUp({
  to,
  from = 0,
  prefix = "",
  suffix = "",
  decimals = 0,
  duration = 1.4,
  trigger = "scroll",
  className,
}: CountUpProps) {
  const ref = useRef<HTMLSpanElement>(null);
  const format = (value: number) =>
    `${prefix}${new Intl.NumberFormat("en-US", {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    }).format(value)}${suffix}`;

  useGSAP(
    () => {
      const element = ref.current;
      if (!element) return undefined;
      const media = gsap.matchMedia();
      media.add(MOTION_OK, () => {
        const state = { value: from };
        const write = () => {
          element.textContent = format(state.value);
        };
        gsap.set(element, { willChange: "transform, opacity" });
        const tween = gsap.to(state, {
          value: to,
          duration,
          ease: "power2.out",
          paused: trigger === "scroll",
          onUpdate: write,
          onComplete: () => {
            element.textContent = format(to);
            gsap.set(element, { clearProps: "willChange" });
          },
        });
        const scrollTrigger =
          trigger === "scroll"
            ? ScrollTrigger.create({
                trigger: element,
                start: "top 92%",
                once: true,
                onEnter: () => tween.play(),
              })
            : undefined;
        if (trigger === "load") write();

        return () => {
          scrollTrigger?.kill();
          tween.kill();
          element.textContent = format(to);
        };
      });
      return () => media.revert();
    },
    { scope: ref },
  );

  return <span ref={ref} className={cn("tabular-nums", className)}>{format(to)}</span>;
}
