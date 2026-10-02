import { useRef } from "react";
import { gsap, useGSAP, ScrollTrigger, MOTION_OK } from "@/lib/gsap";
import { cn, formatNumber } from "@/lib/utils";

interface AnimatedCounterProps {
  value: number;
  /** "percent" renders 0.62 as "62%"; "number" renders 1,248. */
  format?: "percent" | "number" | "raw";
  decimals?: number;
  prefix?: string;
  suffix?: string;
  duration?: number;
  className?: string;
}

/**
 * Counts up from 0 to `value` when the element scrolls into view
 * (GSAP-tweened, once). Reduced-motion: renders the final value.
 */
export function AnimatedCounter({
  value,
  format = "number",
  decimals,
  prefix = "",
  suffix = "",
  duration = 1.6,
  className,
}: AnimatedCounterProps) {
  const ref = useRef<HTMLSpanElement>(null);

  const render = (current: number): string => {
    if (format === "percent") return `${(current * 100).toFixed(decimals ?? 0)}%`;
    if (format === "raw") return current.toFixed(decimals ?? 0);
    return formatNumber(Math.round(current));
  };

  useGSAP(
    () => {
      const el = ref.current;
      if (!el) return undefined;

      const write = (v: number) => {
        el.textContent = `${prefix}${render(v)}${suffix}`;
      };

      const mm = gsap.matchMedia();
      mm.add(MOTION_OK, () => {
        const state = { v: 0 };
        const tween = gsap.to(state, {
          v: value,
          duration,
          ease: "power3.out",
          paused: true,
          onUpdate: () => write(state.v),
        });
        const st = ScrollTrigger.create({
          trigger: el,
          start: "top 92%",
          once: true,
          onEnter: () => tween.play(),
        });
        return () => {
          st.kill();
          tween.kill();
        };
      });
      mm.add("(prefers-reduced-motion: reduce)", () => {
        write(value);
        return undefined;
      });
      return () => mm.revert();
    },
    { scope: ref },
  );

  return (
    <span ref={ref} className={cn("tabular-nums", className)}>
      {prefix}
      {render(value)}
      {suffix}
    </span>
  );
}
