import { useRef } from "react";
import { gsap, useGSAP, MOTION_OK } from "@/lib/gsap-config";
import { LOGOS } from "@/data/features";

function LogoRow({ ariaHidden = false }: { ariaHidden?: boolean }) {
  return (
    <div className="flex w-max items-center gap-14 pr-14" aria-hidden={ariaHidden}>
      {LOGOS.map(({ name, Icon, asset }) => (
        <span
          key={name}
          className="flex items-center gap-2.5 text-muted-foreground/65 grayscale transition-all duration-300 hover:text-foreground hover:grayscale-0"
        >
          {asset ? (
            <img src={asset} alt="" loading="lazy" className="size-5 object-contain" />
          ) : (
            <Icon className="size-5" strokeWidth={1.75} aria-hidden="true" />
          )}
          <span className="font-heading text-[16px] font-semibold tracking-[-0.02em]">{name}</span>
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
          duration: half / 42,
          repeat: -1,
        });
        return () => tween.kill();
      });
      mm.add("(prefers-reduced-motion: reduce)", () => {
        const clone = track.children[1] as HTMLElement | undefined;
        track.classList.add("logo-cloud-track-static");
        if (clone) clone.hidden = true;
        return () => {
          track.classList.remove("logo-cloud-track-static");
          if (clone) clone.hidden = false;
        };
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
