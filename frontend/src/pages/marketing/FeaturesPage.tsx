import { useSplitText } from "@/hooks/useSplitText";
import { useReveal } from "@/hooks/useScrollTrigger";
import { AnimatedCounter } from "@/components/shared/AnimatedCounter";
import { Navbar } from "@/components/marketing/Navbar";
import { FeatureBento } from "@/components/marketing/FeatureBento";
import { StochasticDemo } from "@/components/marketing/StochasticDemo";
import { FinalCTA } from "@/components/marketing/FinalCTA";
import { Footer } from "@/components/marketing/Footer";

const STATS = [
  { label: "Samples per query, per engine", render: () => <AnimatedCounter value={10} format="number" duration={1} /> },
  { label: "Typical interval half-width", render: () => <AnimatedCounter value={5} format="raw" prefix="±" suffix="pp" duration={1} /> },
  { label: "NLI precision on eval set", render: () => <AnimatedCounter value={0.94} format="percent" decimals={0} duration={1.4} /> },
  { label: "Engines in general availability", render: () => <AnimatedCounter value={3} format="number" duration={1} /> },
];

export default function FeaturesPage() {
  const headlineRef = useSplitText<HTMLHeadingElement>({ kind: "words", scroll: false, delay: 0.1 });
  const statsRef = useReveal<HTMLDivElement>({ stagger: 0.1 });

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="pt-16">
        <section className="relative overflow-hidden px-4 py-24 sm:px-6 md:py-28 lg:px-8">
          <div
            aria-hidden="true"
            className="pointer-events-none absolute left-1/2 top-[-240px] h-[480px] w-[720px] -translate-x-1/2 rounded-full bg-accent/[0.11] blur-[130px]"
          />
          <div className="relative mx-auto max-w-3xl text-center">
            <p className="font-mono text-xs font-medium uppercase tracking-[0.18em] text-accent">
              Features
            </p>
            <h1 ref={headlineRef} className="mt-4 font-heading text-display text-foreground">
              The measurement stack for AI search.
            </h1>
            <p className="mx-auto mt-5 max-w-xl text-body-lg text-muted-foreground">
              Crawl, simulate, sample, verify. Every stage is observable — every conclusion
              carries an interval.
            </p>
          </div>

          <div ref={statsRef} className="mx-auto mt-16 grid max-w-5xl grid-cols-2 gap-4 lg:grid-cols-4">
            {STATS.map((stat) => (
              <div key={stat.label} data-reveal className="rounded-xl border border-border bg-card p-6 text-center">
                <p className="font-heading text-4xl font-semibold tracking-[-0.02em] text-foreground">
                  {stat.render()}
                </p>
                <p className="mt-2 text-xs text-muted-foreground">{stat.label}</p>
              </div>
            ))}
          </div>
        </section>

        <FeatureBento />
        <StochasticDemo />
        <FinalCTA />
      </main>
      <Footer />
    </div>
  );
}
