import Lenis from "lenis";
import {
  createContext,
  createElement,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { gsap, ScrollTrigger } from "@/lib/gsap-config";

const LenisContext = createContext<Lenis | null>(null);

/**
 * Runs Lenis from the GSAP ticker and keeps ScrollTrigger in sync each frame.
 * Smooth scrolling is disabled for reduced-motion users and touch-first devices.
 */
export function LenisProvider({ children }: { children: ReactNode }) {
  const [lenis, setLenis] = useState<Lenis | null>(null);

  useEffect(() => {
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const touchFirst = window.matchMedia("(pointer: coarse)").matches;
    if (reducedMotion || touchFirst) return undefined;

    const instance = new Lenis({
      lerp: 0.12,
      smoothWheel: true,
      syncTouch: false,
      wheelMultiplier: 0.9,
    });

    const tick = (time: number) => {
      instance.raf(time * 1000);
      ScrollTrigger.update();
    };

    instance.on("scroll", ScrollTrigger.update);
    gsap.ticker.add(tick);
    gsap.ticker.lagSmoothing(0);
    const stateFrame = window.requestAnimationFrame(() => setLenis(instance));

    return () => {
      window.cancelAnimationFrame(stateFrame);
      gsap.ticker.remove(tick);
      instance.off("scroll", ScrollTrigger.update);
      instance.destroy();
    };
  }, []);

  return createElement(LenisContext.Provider, { value: lenis }, children);
}

export function useLenis(): Lenis | null {
  return useContext(LenisContext);
}

export function scrollToTarget(lenis: Lenis | null, selector: string): void {
  const element = document.querySelector<HTMLElement>(selector);
  if (!element) return;

  if (lenis) {
    lenis.scrollTo(element, { offset: -80, duration: 1.1 });
    return;
  }

  element.scrollIntoView({ behavior: "auto", block: "start" });
}
