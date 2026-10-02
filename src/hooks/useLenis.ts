import Lenis from "lenis";
import { createContext, createElement, useContext, useEffect, useState, type ReactNode } from "react";
import { gsap, ScrollTrigger } from "@/lib/gsap";

const LenisContext = createContext<Lenis | null>(null);

/**
 * Provides a Lenis smooth-scroll instance wired into GSAP's ticker so
 * ScrollTrigger and Lenis stay in perfect sync. Disabled entirely for
 * users who prefer reduced motion.
 */
export function LenisProvider({ children }: { children: ReactNode }) {
  const [lenis, setLenis] = useState<Lenis | null>(null);

  useEffect(() => {
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduced) return undefined;

    const instance = new Lenis({ lerp: 0.11, smoothWheel: true });
    instance.on("scroll", ScrollTrigger.update);

    const tick = (time: number) => instance.raf(time * 1000);
    gsap.ticker.add(tick);
    gsap.ticker.lagSmoothing(0);
    setLenis(instance);

    return () => {
      gsap.ticker.remove(tick);
      instance.destroy();
      setLenis(null);
    };
  }, []);

  return createElement(LenisContext.Provider, { value: lenis }, children);
}

/** Access the global Lenis instance (null under reduced motion). */
export function useLenis(): Lenis | null {
  return useContext(LenisContext);
}

/** Smoothly scroll to a CSS selector, honoring Lenis when active. */
export function scrollToTarget(lenis: Lenis | null, selector: string): void {
  const el = document.querySelector(selector);
  if (!el) return;
  if (lenis) {
    lenis.scrollTo(el as HTMLElement, { offset: -80, duration: 1.4 });
  } else {
    (el as HTMLElement).scrollIntoView({ behavior: "auto", block: "start" });
  }
}
