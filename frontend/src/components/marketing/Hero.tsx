import { useRef } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Play, Sparkles } from "lucide-react";
import { gsap, useGSAP, MOTION_OK } from "@/lib/gsap-config";
import { useSplitText } from "@/hooks/useSplitText";
import { scrollToTarget, useLenis } from "@/hooks/useLenis";
import { GradientText } from "@/components/shared/GradientText";
import { MagneticButton } from "@/components/shared/MagneticButton";
import { Button } from "@/components/ui/button";
import { STOCHASTIC_SAMPLES, STOCHASTIC_MEAN, STOCHASTIC_BAND } from "@/data/mock-metrics";

const BAR_VALUES = STOCHASTIC_SAMPLES.map((s) => s.probability);
const Y_MIN = 0.4;
const Y_MAX = 0.85;
const CHART_H = 200;
const CHART_W = 520;

function yFor(value: number): number {
  const t = (value - Y_MIN) / (Y_MAX - Y_MIN);
  return CHART_H - t * CHART_H;
}

/** Animated CPI dashboard mockup — bars scrub in as the hero scrolls. */
function DashboardMockup() {
  const ref = useRef<HTMLDivElement>(null);

  useGSAP(
    () => {
      const root = ref.current;
      if (!root) return undefined;
      const mm = gsap.matchMedia();
      mm.add(MOTION_OK, () => {
        const bars = root.querySelectorAll<SVGRectElement>("[data-bar]");
        const band = root.querySelector<SVGRectElement>("[data-band]");
        const mean = root.querySelector<SVGLineElement>("[data-mean]");

        gsap.set(bars, { scaleY: 0, transformOrigin: "50% 100%" });
        if (band) gsap.set(band, { opacity: 0 });
        if (mean) gsap.set(mean, { opacity: 0, scaleX: 0, transformOrigin: "0% 50%" });

        const tl = gsap.timeline({
          scrollTrigger: { trigger: root, start: "top 88%", end: "top 35%", scrub: 1 },
        });
        tl.to(bars, { scaleY: 1, stagger: 0.06, ease: "power2.out" })
          .to(mean, { opacity: 1, scaleX: 1, ease: "none" }, "-=0.2")
          .to(band, { opacity: 1, ease: "none" }, "-=0.1");

        gsap.to(root, {
          yPercent: -6,
          ease: "none",
          scrollTrigger: { trigger: root, start: "top bottom", end: "bottom top", scrub: 1.2 },
        });
      });
      return () => mm.revert();
    },
    { scope: ref },
  );

  return (
    <div ref={ref} className="relative mx-auto mt-16 w-full max-w-3xl will-change-transform">
      <div
        aria-hidden="true"
        className="absolute -inset-x-8 -top-10 bottom-0 rounded-[32px] bg-accent/10 blur-3xl"
      />
      <div className="relative overflow-hidden rounded-2xl border border-border bg-card shadow-card-hover">
        {/* Window chrome */}
        <div className="flex items-center gap-3 border-b border-border px-5 py-3">
          <div className="flex gap-1.5" aria-hidden="true">
            <span className="size-2.5 rounded-full bg-border" />
            <span className="size-2.5 rounded-full bg-border" />
            <span className="size-2.5 rounded-full bg-border" />
          </div>
          <p className="font-mono text-xs text-muted-foreground">xgeo / audits / brand-queries</p>
          <span className="ml-auto inline-flex items-center gap-1.5 rounded-full border border-success/30 bg-success/10 px-2.5 py-0.5 text-xs font-medium text-success">
            <span className="size-1.5 rounded-full bg-success" />
            sampling
          </span>
        </div>

        <div className="grid gap-6 p-6 sm:grid-cols-[180px_1fr]">
          <div className="flex flex-col justify-between gap-6">
            <div>
              <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">
                Citation probability
              </p>
              <p className="mt-2 font-heading text-[44px] font-semibold leading-none tracking-[-0.03em] text-foreground">
                0.62
              </p>
              <p className="mt-1.5 font-mono text-xs text-accent">[0.57, 0.67] · 95% CI</p>
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between rounded-lg border border-border bg-background/50 px-3 py-2">
                <span className="text-xs text-muted-foreground">Samples</span>
                <span className="font-mono text-xs text-foreground">N=10</span>
              </div>
              <div className="flex items-center justify-between rounded-lg border border-border bg-background/50 px-3 py-2">
                <span className="text-xs text-muted-foreground">Δ vs last wk</span>
                <span className="font-mono text-xs text-success">+4.1pp</span>
              </div>
            </div>
          </div>

          <div className="relative">
            <svg
              viewBox={`0 0 ${CHART_W} ${CHART_H}`}
              className="h-auto w-full"
              role="img"
              aria-label="Ten Monte Carlo citation samples distributed around a 0.62 mean with a confidence band"
            >
              {[0.45, 0.55, 0.65, 0.75].map((tick) => (
                <g key={tick}>
                  <line
                    x1={0} x2={CHART_W} y1={yFor(tick)} y2={yFor(tick)}
                    stroke="hsl(var(--border))" strokeDasharray="3 5" strokeWidth="1"
                  />
                  <text x={4} y={yFor(tick) - 5} className="fill-muted-foreground" fontSize="10" fontFamily="Geist Mono, monospace">
                    {tick.toFixed(2)}
                  </text>
                </g>
              ))}
              <rect
                data-band
                x={0} width={CHART_W}
                y={yFor(STOCHASTIC_MEAN + STOCHASTIC_BAND)}
                height={yFor(STOCHASTIC_MEAN - STOCHASTIC_BAND) - yFor(STOCHASTIC_MEAN + STOCHASTIC_BAND)}
                fill="hsl(var(--accent))" fillOpacity="0.09"
              />
              <line
                data-mean
                x1={0} x2={CHART_W}
                y1={yFor(STOCHASTIC_MEAN)} y2={yFor(STOCHASTIC_MEAN)}
                stroke="hsl(var(--accent))" strokeWidth="1.5" strokeDasharray="6 4"
              />
              {BAR_VALUES.map((value, i) => {
                const barW = CHART_W / BAR_VALUES.length;
                const x = i * barW + barW * 0.28;
                const y = yFor(value);
                return (
                  <rect
                    key={i}
                    data-bar
                    x={x}
                    y={y}
                    width={barW * 0.44}
                    height={CHART_H - y}
                    rx={3}
                    fill={value >= STOCHASTIC_MEAN ? "hsl(var(--accent))" : "hsl(var(--muted-foreground) / 0.45)"}
                  />
                );
              })}
            </svg>
            <div className="mt-2 flex justify-between font-mono text-[10px] text-muted-foreground">
              <span>run 01 · τ 0.2</span>
              <span>temperature sweep →</span>
              <span>run 10 · τ 1.0</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export function Hero() {
  const headlineRef = useSplitText<HTMLHeadingElement>({
    kind: "words",
    scroll: false,
    blur: true,
    delay: 0.15,
    stagger: 0.07,
  });
  const lenis = useLenis();
  const fadeRef = useRef<HTMLDivElement>(null);

  useGSAP(
    () => {
      const mm = gsap.matchMedia();
      mm.add(MOTION_OK, () => {
        gsap.from("[data-hero-fade]", {
          y: 20,
          opacity: 0,
          duration: 0.9,
          stagger: 0.12,
          delay: 0.7,
          ease: "power3.out",
        });
      });
      return () => mm.revert();
    },
    { scope: fadeRef },
  );

  return (
    <section className="relative overflow-hidden pt-36 pb-24 md:pt-44" ref={fadeRef}>
      {/* Ambient background */}
      <div aria-hidden="true" className="pointer-events-none absolute inset-0">
        <div className="absolute left-1/2 top-[-320px] h-[640px] w-[900px] -translate-x-1/2 rounded-full bg-accent/[0.13] blur-[140px] animate-gradient-pan" />
        <div className="absolute right-[-200px] top-[300px] h-[400px] w-[400px] rounded-full bg-accent/[0.07] blur-[120px] animate-gradient-pan-alt" />
        <div
          className="absolute inset-0 opacity-[0.35] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,black,transparent)]"
          style={{
            backgroundImage:
              "linear-gradient(hsl(var(--border) / 0.55) 1px, transparent 1px), linear-gradient(90deg, hsl(var(--border) / 0.55) 1px, transparent 1px)",
            backgroundSize: "56px 56px",
          }}
        />
      </div>

      <div className="relative mx-auto max-w-5xl px-4 text-center sm:px-6">
        <div data-hero-fade>
          <Link
            to="/docs"
            className="group inline-flex items-center gap-2 rounded-full border border-border bg-card/70 py-1.5 pl-2 pr-4 text-xs font-medium text-muted-foreground backdrop-blur transition-all hover:border-accent/40 hover:text-foreground"
          >
            <span className="grid size-5 place-items-center rounded-full bg-accent/15 text-accent">
              <Sparkles className="size-3" />
            </span>
            Introducing Monte Carlo CPI tracking
            <ArrowRight className="size-3 transition-transform duration-300 group-hover:translate-x-0.5" />
          </Link>
        </div>

        <h1 ref={headlineRef} className="mt-8 font-heading text-hero text-foreground">
          Stop guessing if AI cites your brand. <GradientText>Measure it with confidence.</GradientText>
        </h1>

        <p
          data-hero-fade
          className="mx-auto mt-6 max-w-2xl text-body-lg text-muted-foreground"
        >
          X-GEO runs Monte Carlo simulations across AI search engines to deliver statistically
          stable citation probability intervals — not single-snapshot guesses.
        </p>

        <div data-hero-fade className="mt-10 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <MagneticButton>
            <Button variant="accent" size="lg" asChild>
              <Link to="/signup">
                Start Free Audit
                <ArrowRight className="size-4" />
              </Link>
            </Button>
          </MagneticButton>
          <Button
            variant="ghost"
            size="lg"
            onClick={() => scrollToTarget(lenis, "#demo")}
            className="group"
          >
            <Play className="size-4 text-accent transition-transform duration-300 group-hover:scale-110" />
            Watch Demo
          </Button>
        </div>

        <p data-hero-fade className="mt-6 text-xs text-muted-foreground">
          No credit card required
          <span className="mx-2.5 text-border">·</span>
          10 free audits
          <span className="mx-2.5 text-border">·</span>
          SOC 2 Type II ready
        </p>
      </div>

      <div className="px-4 sm:px-6">
        <DashboardMockup />
      </div>
    </section>
  );
}
