import { useRef } from "react";
import { gsap, useGSAP, MOTION_OK } from "@/lib/gsap";
import { LOGOS } from "@/lib/mock-data";

function LogoRow({ ariaHidden = false }: { ariaHidden?: boolean }) {
  return (
    <div className="flex w-max items-center gap-14 pr-14" aria-hidden={ariaHidden}>
      {LOGOS.map(({ name, Icon }) => (
        <span
          key={name}
          className="flex items-center gap-2.5 text-muted-foreground/70 grayscale transition-all duration-300 hover:text-foreground hover:grayscale-0"
        >
          <Icon className="size-5" strokeWidth={1.75} />
          <span className="font-heading text-[17px] font-semibold tracking-[-0.01em]">{name}</span>
        </span>
      ))}
    </div>
  );
}

/**
 * Infinite logo marquee — one GSAP timeline, xPercent -50 loop,
 * duration derived from measured width so speed is constant.
 * Reduced motion: static wrapped row.
 */
export function LogoCloud() {
  const trackRef = useRef<HTMLDivElement>(null);

  useGSAP(
    () => {
      const track = trackRef.current;
      if (!track) return undefined;
      const mm = gsap.matchMedia();
      mm.add(MOTION_OK, () => {
        const half = track.scrollWidth / 2;
        const tween = gsap.to(track, {
          x: -half,
          ease: "none",
          duration: half / 42, // ~42 px/s — smooth, never stutters
          repeat: -1,
        });
        return () => tween.kill();
      });
      return () => mm.revert();
    },
    { scope: trackRef },
  );

  return (
    <section className="border-y border-border/60 py-14">
      <p className="text-center text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">
        Trusted by content teams at
      </p>
      <div className="mask-fade-x mt-8 overflow-hidden">
        <div ref={trackRef} className="flex w-max will-change-transform">
          <LogoRow />
          <LogoRow ariaHidden />
        </div>
      </div>
    </section>
  );
}
