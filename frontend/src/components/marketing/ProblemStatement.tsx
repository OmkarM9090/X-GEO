import { useRef } from "react";
import { ArrowDownRight, ArrowUpRight, CircleAlert } from "lucide-react";
import { AnimatedCounter } from "@/components/shared/AnimatedCounter";
import { SectionHeading } from "@/components/shared/SectionHeading";
import { useReveal } from "@/hooks/useScrollTrigger";
import { cn } from "@/lib/utils";

const STATS = [
  {
    value: 25.8,
    decimals: 1,
    label: "of searches show AI Overviews",
    context: "Google's expanding answer layer",
    tone: "neutral",
  },
  {
    value: 38,
    decimals: 0,
    label: "traffic drop for news publishers",
    context: "when an overview answers the query",
    tone: "danger",
  },
  {
    value: 57,
    decimals: 0,
    label: "of RAG citations are unfaithful",
    context: "without source-level verification",
    tone: "warning",
  },
] as const;

/** A restrained, evidence-led statement of the zero-click problem. */
export function ProblemStatement() {
  const cardsRef = useReveal<HTMLDivElement>({
    selector: "[data-problem-stat]",
    y: 22,
    scale: 0.9,
    stagger: 0.1,
    start: "top 82%",
    duration: 0.7,
  });
  const copyRef = useRef<HTMLParagraphElement>(null);

  return (
    <section className="px-4 py-24 sm:px-6 md:py-32 lg:px-8">
      <div className="mx-auto w-full max-w-5xl">
        <SectionHeading
          eyebrow="The zero-click shift"
          title="AI search is replacing your clicks with zero-click answers."
          description="Visibility is no longer a position on a results page. It is whether an engine chooses, trusts, and cites your content."
          size="display"
          className="max-w-4xl"
        />

        <div ref={cardsRef} className="mt-12 grid gap-4 md:grid-cols-3">
          {STATS.map((stat, index) => (
            <article
              key={stat.label}
              data-problem-stat
              data-cursor="interactive"
              className={cn(
                "group relative overflow-hidden rounded-2xl border border-border bg-card p-6 shadow-card transition-colors duration-300 hover:border-foreground/20 sm:p-8",
                index === 1 && "border-danger/20",
              )}
            >
              <div aria-hidden="true" className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-foreground/10 to-transparent" />
              <div className="flex items-center justify-between gap-3">
                <p className="font-mono text-[10px] uppercase tracking-[0.15em] text-muted-foreground">
                  Signal 0{index + 1}
                </p>
                {stat.tone === "danger" ? (
                  <ArrowDownRight className="size-4 text-danger" aria-hidden="true" />
                ) : stat.tone === "warning" ? (
                  <CircleAlert className="size-4 text-warning" aria-hidden="true" />
                ) : (
                  <ArrowUpRight className="size-4 text-accent" aria-hidden="true" />
                )}
              </div>
              <p className={cn(
                "mt-8 font-mono text-5xl font-semibold tracking-[-0.07em] text-foreground sm:text-6xl",
                stat.tone === "danger" && "text-danger",
                stat.tone === "warning" && "text-warning",
              )}>
                <AnimatedCounter
                  value={stat.value}
                  format="raw"
                  decimals={stat.decimals}
                  suffix="%"
                  duration={1.25}
                />
              </p>
              <p className="mt-4 text-sm font-medium text-foreground">{stat.label}</p>
              <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">{stat.context}</p>
            </article>
          ))}
        </div>

        <p ref={copyRef} className="mx-auto mt-10 max-w-3xl text-center text-base leading-relaxed text-muted-foreground sm:text-lg">
          Commercial tools scrape once and guess. <span className="text-foreground">X-GEO runs Monte Carlo simulations</span> to give you real confidence intervals — and a defensible signal when the answer changes.
        </p>
      </div>
    </section>
  );
}
