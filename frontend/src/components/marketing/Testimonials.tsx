import { useRef } from "react";
import { Quote } from "lucide-react";
import { gsap, useGSAP } from "@/lib/gsap-config";
import { useSplitText } from "@/hooks/useSplitText";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { TESTIMONIALS } from "@/data/testimonials";

/**
 * Horizontal scroll hijack: on desktop the section pins and the card
 * track translates with vertical scroll (scrub 1). On mobile and for
 * reduced-motion users it degrades to a native snap-x scroller.
 */
export function Testimonials() {
  const headlineRef = useSplitText<HTMLHeadingElement>({ kind: "lines" });
  const sectionRef = useRef<HTMLElement>(null);
  const trackRef = useRef<HTMLDivElement>(null);

  useGSAP(
    () => {
      const track = trackRef.current;
      if (!track) return undefined;

      const mm = gsap.matchMedia();
      mm.add("(min-width: 768px) and (prefers-reduced-motion: no-preference)", () => {
        const distance = () => Math.max(0, track.scrollWidth - window.innerWidth + 96);
        const tween = gsap.to(track, {
          x: () => -distance(),
          ease: "none",
          scrollTrigger: {
            trigger: sectionRef.current,
            start: "top top",
            end: () => `+=${distance()}`,
            scrub: 1,
            pin: true,
            anticipatePin: 1,
            invalidateOnRefresh: true,
          },
        });
        return () => {
          tween.scrollTrigger?.kill();
          tween.kill();
          gsap.set(track, { clearProps: "x" });
        };
      });
      mm.add("(prefers-reduced-motion: reduce)", () => {
        const scroller = sectionRef.current?.querySelector<HTMLElement>("[data-testimonial-scroller]");
        scroller?.classList.add("testimonial-static-scroll");
        return () => scroller?.classList.remove("testimonial-static-scroll");
      });
      return () => mm.revert();
    },
    { scope: sectionRef },
  );

  return (
    <section
      ref={sectionRef}
      className="relative overflow-hidden py-24 md:flex md:h-screen md:min-h-[720px] md:flex-col md:justify-center md:py-0"
    >
      <div className="mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8">
        <p className="font-mono text-xs font-medium uppercase tracking-[0.18em] text-accent">
          Field notes
        </p>
        <h2 ref={headlineRef} className="mt-4 max-w-2xl font-heading text-display text-foreground">
          Teams that stopped screenshotting chatbots.
        </h2>
      </div>

      <div data-testimonial-scroller className="mt-12 snap-x snap-mandatory overflow-x-auto pb-6 md:mt-16 md:snap-none md:overflow-visible md:pb-0 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        <div
          ref={trackRef}
          className="flex w-max gap-5 px-4 will-change-transform sm:px-6 lg:px-[max(2rem,calc((100vw-1280px)/2+2rem))]"
        >
          {TESTIMONIALS.map((t) => (
            <figure
              key={t.name}
              className="flex h-[280px] w-[320px] shrink-0 snap-start flex-col justify-between rounded-2xl border border-border bg-card p-7 sm:w-[380px]"
            >
              <div>
                <Quote className="size-5 text-accent/60" aria-hidden="true" />
                <blockquote className="mt-4 text-body leading-relaxed text-foreground/90">
                  “{t.quote}”
                </blockquote>
              </div>
              <figcaption className="mt-6 flex items-center gap-3 border-t border-border/70 pt-5">
                <Avatar>
                  <AvatarFallback>{t.initials}</AvatarFallback>
                </Avatar>
                <div>
                  <p className="text-sm font-medium text-foreground">{t.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {t.role} · {t.company}
                  </p>
                </div>
              </figcaption>
            </figure>
          ))}

          <div className="flex h-[280px] w-[260px] shrink-0 snap-start flex-col items-start justify-center rounded-2xl border border-dashed border-border bg-card/40 p-7">
            <p className="font-heading text-4xl font-semibold tracking-[-0.02em] text-foreground">41</p>
            <p className="mt-2 text-sm text-muted-foreground">
              domains in the beta cohort. Median lift: +11pp CPI in six weeks.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
