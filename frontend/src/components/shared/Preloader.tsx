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

/** Ultra-premium cinematic preloader with staggered columns. */
export function Preloader() {
  const [visible, setVisible] = useState(shouldShowPreloader);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!visible) return;
    try {
      window.sessionStorage.setItem(SESSION_KEY, "1");
    } catch {
      // Ignore storage errors
    }
  }, [visible]);

  useGSAP(
    () => {
      const root = rootRef.current;
      if (!visible || !root) return undefined;

      const media = gsap.matchMedia();
      media.add(MOTION_OK, () => {
        const cols = root.querySelectorAll("[data-col]");
        const letters = root.querySelectorAll("[data-letter]");
        const glow = root.querySelector("[data-glow]");
        const subtext = root.querySelector("[data-subtext]");
        
        // Initial state
        gsap.set(letters, { yPercent: 120, rotation: 10, opacity: 0, transformOrigin: "bottom left" });
        gsap.set(subtext, { yPercent: 100, opacity: 0 });
        gsap.set(glow, { opacity: 0, scale: 0.5 });
        
        const timeline = gsap.timeline({
          onComplete: () => setVisible(false),
        });

        timeline
          // 1. Cinematic staggered letters reveal
          .to(letters, { 
            yPercent: 0, 
            rotation: 0, 
            opacity: 1, 
            duration: 0.85, 
            stagger: 0.08, 
            ease: "back.out(1.2)" 
          })
          // 2. Pulse glow and reveal subtext
          .to(glow, { opacity: 1, scale: 1.3, duration: 1, ease: "power2.out" }, "-=0.6")
          .to(subtext, { yPercent: 0, opacity: 1, duration: 0.7, ease: "power3.out" }, "-=0.5")
          
          // 3. Hover pause so the user absorbs the brand
          .to({}, { duration: 0.4 })
          
          // 4. Smoothly pull everything out
          .to(letters, { yPercent: -80, opacity: 0, duration: 0.5, stagger: 0.04, ease: "power2.in" })
          .to(subtext, { yPercent: -50, opacity: 0, duration: 0.4, ease: "power2.in" }, "<")
          .to(glow, { opacity: 0, scale: 2, duration: 0.5 }, "<")
          
          // 5. Staggered column wipe up to reveal the actual website!
          .to(cols, { 
            yPercent: -100, 
            duration: 0.9, 
            stagger: 0.07, 
            ease: "power4.inOut" 
          }, "-=0.3");

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

  const word = "X-GEO".split("");

  return (
    <div
      ref={rootRef}
      className="fixed inset-0 z-[10000] overflow-hidden"
      role="status"
      aria-label="Loading X-GEO"
    >
      {/* 5 Staggered Columns covering the screen */}
      <div className="absolute inset-0 flex">
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} data-col className="h-full flex-1 bg-[#0A0A0B] border-r border-white/[0.02]" />
        ))}
      </div>

      {/* Centered Cinematic Content */}
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <div className="relative flex items-center justify-center">
          <div data-glow className="absolute inset-0 rounded-full bg-accent/30 blur-[50px]" />
          
          <div className="flex overflow-hidden px-4 pb-2 pt-6">
            {word.map((char, index) => (
              <span
                key={index}
                data-letter
                className={`font-heading text-6xl font-bold tracking-tight md:text-8xl drop-shadow-xl ${
                  char === "X" ? "text-accent" : "text-white"
                }`}
              >
                {char}
              </span>
            ))}
          </div>
        </div>
        
        <div className="mt-1 overflow-hidden">
          <div data-subtext className="font-mono text-[10px] tracking-[0.4em] text-white/50 sm:text-xs">
            AI SEARCH CITATIONS
          </div>
        </div>
      </div>
    </div>
  );
}
