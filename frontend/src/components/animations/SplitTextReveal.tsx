import { useRef, type ElementType, type ReactNode } from "react";
import { gsap, useGSAP, SplitText, ScrollTrigger, MOTION_OK } from "@/lib/gsap-config";
import { cn } from "@/lib/utils";

export type SplitTextType = "words" | "chars" | "lines";
export type SplitTextAnimation = "rise" | "scramble" | "blur" | "highlight";
export type SplitTextTrigger = "scroll" | "load";

interface SplitTextRevealProps {
  children: ReactNode;
  type?: SplitTextType;
  animation?: SplitTextAnimation;
  stagger?: number;
  trigger?: SplitTextTrigger;
  /** Portion of the viewport that should be visible before starting, from 0 to 1. */
  threshold?: number;
  duration?: number;
  className?: string;
  as?: ElementType;
  id?: string;
}

const SCRAMBLE_CHARS = "!@#$%^&*()_+=<>?";

function scramble(value: string, progress: number, seed: number): string {
  const letters = Array.from(value);
  const settledCount = Math.floor(letters.length * progress);

  return letters
    .map((character, index) => {
      if (/\s/.test(character) || index < settledCount || progress >= 1) return character;
      const noise = Math.floor(Math.abs(Math.sin(seed * 91.7 + index * 19.13 + progress * 170) * 10_000));
      return SCRAMBLE_CHARS[noise % SCRAMBLE_CHARS.length];
    })
    .join("");
}

/** Text splitting + scroll/load reveal using GSAP SplitText, with a static reduced-motion fallback. */
export function SplitTextReveal({
  children,
  type = "words",
  animation = "rise",
  stagger = 0.08,
  trigger = "scroll",
  threshold = 0.2,
  duration = 0.8,
  className,
  as = "span",
  id,
}: SplitTextRevealProps) {
  const elementRef = useRef<HTMLElement>(null);
  const Component = as;

  useGSAP(
    () => {
      const element = elementRef.current;
      if (!element) return undefined;

      const media = gsap.matchMedia();
      media.add(MOTION_OK, () => {
        let split: SplitText | undefined;
        let triggerInstance: ScrollTrigger | undefined;
        let cancelled = false;
        let playReveal: (() => void) | undefined;

        const prepare = () => {
          if (cancelled || !element.isConnected) return;

          try {
            split = new SplitText(element, {
              type,
              mask: animation === "rise" ? type : undefined,
              aria: "auto",
            });
          } catch {
            // Keep the un-split text readable if a browser font/layout edge case occurs.
            return;
          }

          const units = (type === "words" ? split.words : type === "chars" ? split.chars : split.lines) as HTMLElement[];
          if (!units.length) return;

          gsap.set(units, { willChange: "transform, opacity" });

          if (animation === "highlight") {
            const muted = "hsl(var(--muted-foreground))";
            const foreground = "hsl(var(--foreground))";
            if (trigger === "load") {
              gsap.fromTo(
                units,
                { color: muted },
                {
                  color: foreground,
                  duration,
                  stagger: { each: stagger, from: "start" },
                  ease: "power2.out",
                  clearProps: "willChange",
                },
              );
              return;
            }

            gsap.set(units, { color: muted });
            const highlight = gsap.to(units, {
              color: foreground,
              duration: 1,
              ease: "none",
              stagger: { each: stagger, from: "start" },
              scrollTrigger: {
                trigger: element,
                start: `top ${Math.round(100 - Math.max(0, Math.min(1, threshold)) * 100)}%`,
                end: "bottom 42%",
                scrub: 1,
                invalidateOnRefresh: true,
              },
              onComplete: () => {
                gsap.set(units, { clearProps: "willChange" });
              },
            });
            triggerInstance = highlight.scrollTrigger ?? undefined;
            return;
          }

          if (animation === "scramble") {
            const originals = units.map((unit) => unit.textContent ?? "");
            playReveal = () => {
              units.forEach((unit, index) => {
                const original = originals[index] ?? "";
                const progress = { value: 0 };
                gsap.set(unit, { opacity: 1, y: 0, clearProps: "willChange" });
                gsap.to(progress, {
                  value: 1,
                  duration,
                  delay: index * stagger,
                  ease: "none",
                  onUpdate: () => {
                    unit.textContent = scramble(original, progress.value, index + original.length);
                  },
                  onComplete: () => {
                    unit.textContent = original;
                  },
                });
              });
            };
          } else {
            const from =
              animation === "blur"
                ? { yPercent: 16, opacity: 0, filter: "blur(12px)" }
                : { yPercent: 110, opacity: 0 };
            const to =
              animation === "blur"
                ? { yPercent: 0, opacity: 1, filter: "blur(0px)" }
                : { yPercent: 0, opacity: 1 };

            playReveal = () => {
              gsap.fromTo(units, from, {
                ...to,
                duration,
                stagger,
                ease: "power4.out",
                clearProps: "willChange,filter",
              });
            };
          }

          if (trigger === "load") {
            playReveal?.();
          } else {
            triggerInstance = ScrollTrigger.create({
              trigger: element,
              start: `top ${Math.round(100 - Math.max(0, Math.min(1, threshold)) * 100)}%`,
              once: true,
              onEnter: () => playReveal?.(),
            });
          }
        };

        void document.fonts.ready.then(prepare);
        return () => {
          cancelled = true;
          triggerInstance?.kill();
          split?.revert();
        };
      });

      return () => media.revert();
    },
    { scope: elementRef },
  );

  return (
    <Component ref={elementRef} id={id} className={cn("split-text-reveal", className)}>
      {children}
    </Component>
  );
}
