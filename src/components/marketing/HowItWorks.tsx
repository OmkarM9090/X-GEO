import { useRef } from "react";
import { gsap, useGSAP, MOTION_OK } from "@/lib/gsap";
import { useSplitText } from "@/hooks/useSplitText";
import { HOW_IT_WORKS } from "@/lib/mock-data";

/**
 * Sticky stack: each stage card pins at top-96px and the next one
 * slides over it; the covered card scales down and dims (scrub).
 */
export function HowItWorks() {
  const headlineRef = useSplitText<HTMLHeadingElement>({ kind: "lines" });
  const rootRef = useRef<HTMLDivElement>(null);

  useGSAP(
    () => {
      const root = rootRef.current;
      if (!root) return undefined;
      const mm = gsap.matchMedia();
      mm.add(MOTION_OK, () => {
        const cards = gsap.utils.toArray<HTMLElement>(root.querySelectorAll("[data-stack-card]"));
        const tweens: gsap.core.Tween[] = [];
        cards.forEach((card, i) => {
          if (i === cards.length - 1) return;
          const next = cards[i + 1];
          tweens.push(
            gsap.to(card, {
              scale: 0.93,
              opacity: 0.45,
              transformOrigin: "center top",
              ease: "none",
              scrollTrigger: {
                trigger: next,
                start: "top 95%",
                end: "top 12%",
                scrub: true,
              },
            }),
          );
        });
        return () =>
          tweens.forEach((t) => {
            t.scrollTrigger?.kill();
            t.kill();
          });
      });
      return () => mm.revert();
    },
    { scope: rootRef },
  );

  return (
    <section id="how-it-works" className="py-24 md:py-32">
      <div className="mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <p className="font-mono text-xs font-medium uppercase tracking-[0.18em] text-accent">
            Methodology
          </p>
          <h2 ref={headlineRef} className="mt-4 font-heading text-display text-foreground">
            Four stages. One closed loop.
          </h2>
          <p className="mt-5 text-body-lg text-muted-foreground">
            From raw HTML to a repaired, re-measured chunk — the same pipeline runs for every
            query, every week.
          </p>
        </div>

        <div ref={rootRef} className="mt-16">
          {HOW_IT_WORKS.map((step, i) => (
            <div key={step.index} className="sticky top-24 pb-8" style={{ zIndex: i + 1 }}>
              <article
                data-stack-card
                className="grid min-h-[340px] gap-8 rounded-2xl border border-border bg-card p-8 shadow-card will-change-transform md:min-h-[380px] md:grid-cols-[200px_1fr_auto] md:items-center md:gap-14 md:p-14"
              >
                <div className="flex items-center gap-5 md:flex-col md:items-start md:gap-6">
                  <span className="font-mono text-5xl font-semibold tracking-tight text-accent/50 md:text-6xl">
                    {step.index}
                  </span>
                  <span className="grid size-12 place-items-center rounded-xl border border-accent/25 bg-accent/10 text-accent">
                    <step.Icon className="size-5" strokeWidth={1.75} />
                  </span>
                </div>
                <div>
                  <h3 className="font-heading text-h2 text-foreground">{step.title}</h3>
                  <p className="mt-2 text-body-lg font-medium text-foreground/85">{step.description}</p>
                  <p className="mt-4 max-w-xl text-body text-muted-foreground">{step.detail}</p>
                </div>
                <div className="hidden font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground/60 md:block md:rotate-90 md:whitespace-nowrap">
                  stage {step.index} / 04
                </div>
              </article>
            </div>
          ))}
          <div className="h-[6vh]" aria-hidden="true" />
        </div>
      </div>
    </section>
  );
}
