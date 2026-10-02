import { useRef } from "react";
import { gsap, useGSAP, SplitText, MOTION_OK } from "@/lib/gsap-config";

interface SplitOptions {
  /** Split granularity. */
  kind?: "words" | "lines";
  /** Animate on scroll into view (true) or immediately on mount (false). */
  scroll?: boolean;
  delay?: number;
  start?: string;
  stagger?: number;
  /** Add a blur-out to the rise (hero headline). */
  blur?: boolean;
  duration?: number;
}

/**
 * Splits the referenced element's text content and animates the fragments
 * rising into place. Runs only when motion is allowed; otherwise the text
 * is simply rendered. Waits for webfonts so line splits measure correctly.
 * The split is reverted on cleanup.
 */
export function useSplitText<T extends HTMLElement = HTMLHeadingElement>(options: SplitOptions = {}) {
  const {
    kind = "words",
    scroll = true,
    delay = 0,
    start = "top 85%",
    stagger = 0.08,
    blur = false,
    duration = 0.9,
  } = options;

  const ref = useRef<T>(null);

  useGSAP(
    () => {
      const el = ref.current;
      if (!el) return undefined;

      const mm = gsap.matchMedia();
      mm.add(MOTION_OK, () => {
        let split: SplitText | null = null;
        let tween: gsap.core.Tween | null = null;
        let cancelled = false;

        // Font loading changes line breaks — split only once fonts settle.
        void document.fonts.ready.then(() => {
          if (cancelled || !el.isConnected) return;
          split = new SplitText(el, { type: kind });
          const targets = (kind === "words" ? split.words : split.lines) as HTMLElement[];
          if (targets.length === 0) return;

          gsap.set(targets, { willChange: "transform, opacity" });
          tween = gsap.from(targets, {
            yPercent: 110,
            opacity: 0,
            ...(blur ? { filter: "blur(8px)" } : {}),
            duration,
            ease: "power4.out",
            stagger: kind === "words" ? stagger : 0.12,
            delay,
            clearProps: "willChange,filter",
            scrollTrigger: scroll ? { trigger: el, start, once: true } : undefined,
          });
        });

        return () => {
          cancelled = true;
          tween?.scrollTrigger?.kill();
          tween?.kill();
          split?.revert();
        };
      });

      return () => mm.revert();
    },
    { scope: ref },
  );

  return ref;
}
