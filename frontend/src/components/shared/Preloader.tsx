import { useEffect, useRef, useState } from "react";
import { gsap, useGSAP, MOTION_OK } from "@/lib/gsap-config";

const SESSION_KEY = "xgeo:preloader-shown";

function shouldShowPreloader(): boolean {
  if (typeof window === "undefined") return false;
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return false;
  try {
    return window.sessionStorage.getItem(SESSION_KEY) !== "1";
  } catch {
    return false;
  }
}

/** First-load-only brand card; the complete timeline is capped below 1.8 seconds. */
export function Preloader() {
  const [visible, setVisible] = useState(shouldShowPreloader);
  const rootRef = useRef<HTMLDivElement>(null);
  const wordmarkRef = useRef<HTMLSpanElement>(null);
  const progressRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (!visible) return;
    try {
      window.sessionStorage.setItem(SESSION_KEY, "1");
    } catch {
      // The preloader still completes when storage is disabled.
    }
  }, [visible]);

  useGSAP(
    () => {
      const root = rootRef.current;
      const wordmark = wordmarkRef.current;
      const progress = progressRef.current;
      if (!visible || !root || !wordmark || !progress) return undefined;

      const media = gsap.matchMedia();
      media.add(MOTION_OK, () => {
        gsap.set(progress, { scaleX: 0, transformOrigin: "left center", willChange: "transform, opacity" });
        const timeline = gsap.timeline({
          onComplete: () => setVisible(false),
        });
        timeline
          .fromTo(wordmark, { opacity: 0, scale: 0.95 }, { opacity: 1, scale: 1, duration: 0.3, ease: "power2.out" })
          .to(progress, { scaleX: 1, duration: 1.15, ease: "power2.inOut" }, 0.12)
          .to(root, { yPercent: -100, duration: 0.35, ease: "power4.inOut" }, 1.35);

        return () => timeline.kill();
      });
      media.add("(prefers-reduced-motion: reduce)", () => {
        setVisible(false);
      });
      return () => media.revert();
    },
    { scope: rootRef, dependencies: [visible], revertOnUpdate: true },
  );

  if (!visible) return null;

  return (
    <div
      ref={rootRef}
      className="fixed inset-0 z-[10000] grid place-items-center bg-[#0A0A0B] text-white"
      role="status"
      aria-label="Loading X-GEO"
    >
      <span
        ref={wordmarkRef}
        className="font-heading text-2xl font-semibold tracking-[0.22em] text-white"
      >
        X-GEO
      </span>
      <span className="absolute inset-x-0 bottom-0 h-[2px] overflow-hidden bg-white/10">
        <span ref={progressRef} className="block h-full origin-left bg-gradient-to-r from-violet-400 to-violet-200" />
      </span>
    </div>
  );
}
