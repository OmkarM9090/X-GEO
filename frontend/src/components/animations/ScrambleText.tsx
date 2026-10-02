import { useRef, type ReactNode } from "react";
import { gsap, useGSAP, ScrollTrigger, MOTION_OK } from "@/lib/gsap-config";
import { cn } from "@/lib/utils";

const GLYPHS = "!@#$%^&*()_+=<>?";

interface ScrambleTextProps {
  text: string;
  className?: string;
  duration?: number;
  trigger?: "scroll" | "load";
  children?: ReactNode;
}

/** Small, deterministic cyber-text decode that avoids a paid GSAP plugin dependency. */
export function ScrambleText({
  text,
  className,
  duration = 0.8,
  trigger = "load",
  children,
}: ScrambleTextProps) {
  const ref = useRef<HTMLSpanElement>(null);

  useGSAP(
    () => {
      const element = ref.current;
      if (!element) return undefined;
      const media = gsap.matchMedia();

      media.add(MOTION_OK, () => {
        const state = { value: 0 };
        const render = () => {
          const settled = Math.floor(Array.from(text).length * state.value);
          element.textContent = Array.from(text)
            .map((character, index) => {
              if (/\s/.test(character) || index < settled || state.value >= 1) return character;
              const hash = Math.floor(Math.abs(Math.sin(index * 27.4 + state.value * 200) * 100_000));
              return GLYPHS[hash % GLYPHS.length];
            })
            .join("");
        };
        const tween = gsap.to(state, {
          value: 1,
          duration,
          ease: "none",
          paused: trigger === "scroll",
          onUpdate: render,
          onComplete: () => {
            element.textContent = text;
          },
        });
        const scrollTrigger =
          trigger === "scroll"
            ? ScrollTrigger.create({
                trigger: element,
                start: "top 82%",
                once: true,
                onEnter: () => tween.play(),
              })
            : undefined;

        return () => {
          scrollTrigger?.kill();
          tween.kill();
          element.textContent = text;
        };
      });

      return () => media.revert();
    },
    { scope: ref },
  );

  return (
    <span ref={ref} className={cn("inline-block", className)} aria-label={text}>
      {children ?? text}
    </span>
  );
}
