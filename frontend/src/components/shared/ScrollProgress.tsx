import { useRef } from "react";
import { gsap, useGSAP, ScrollTrigger } from "@/lib/gsap-config";

/** Fixed, document-wide scroll position indicator driven by ScrollTrigger. */
export function ScrollProgress() {
  const barRef = useRef<HTMLSpanElement>(null);

  useGSAP(
    () => {
      const bar = barRef.current;
      if (!bar) return undefined;

      gsap.set(bar, { scaleX: 0, transformOrigin: "left center", willChange: "transform, opacity" });
      const trigger = ScrollTrigger.create({
        id: "xgeo-scroll-progress",
        start: 0,
        end: () => ScrollTrigger.maxScroll(window),
        invalidateOnRefresh: true,
        onUpdate: (self) => gsap.set(bar, { scaleX: self.progress }),
      });
      return () => trigger.kill();
    },
    { scope: barRef },
  );

  return (
    <div aria-hidden="true" className="pointer-events-none fixed inset-x-0 top-0 z-[9998] h-[2px]">
      <span ref={barRef} className="block h-full origin-left scale-x-0 bg-gradient-to-r from-violet-400 via-accent to-cyan-300" />
    </div>
  );
}
