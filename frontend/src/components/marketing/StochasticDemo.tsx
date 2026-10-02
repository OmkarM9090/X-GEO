import { useState } from "react";
import {
  CartesianGrid, ComposedChart, ReferenceArea, ReferenceLine, ResponsiveContainer, Scatter, XAxis, YAxis,
} from "recharts";
import { CheckCircle2 } from "lucide-react";
import { useSplitText } from "@/hooks/useSplitText";
import { useReveal, useScrollProgress } from "@/hooks/useScrollTrigger";
import { STOCHASTIC_SAMPLES, STOCHASTIC_MEAN, STOCHASTIC_BAND } from "@/data/mock-metrics";

const BULLETS = [
  "N=10 stratified samples per engine",
  "Temperature sweep from 0.2 to 1.0",
  "95% Wilson score intervals",
  "Drift alerts at ±3σ",
];

function clamp01(v: number): number {
  return Math.min(1, Math.max(0, v));
}

/**
 * USP showcase: 10 Monte Carlo samples scatter around the CPI mean.
 * Scroll-scrubbed: dots land one-by-one, then the confidence band fades in.
 */
export function StochasticDemo() {
  const [progress, setProgress] = useState(0);
  const sectionRef = useScrollProgress<HTMLElement>(setProgress, {
    start: "top 80%",
    end: "center 40%",
  });
  const headlineRef = useSplitText<HTMLHeadingElement>({ kind: "lines" });
  const listRef = useReveal<HTMLUListElement>({ stagger: 0.07 });

  const dotCount = Math.min(10, Math.floor(clamp01(progress * 1.25) * 10));
  const bandT = clamp01((progress - 0.72) / 0.2);
  const visible = STOCHASTIC_SAMPLES.slice(0, dotCount);

  return (
    <section id="demo" ref={sectionRef} className="py-24 md:py-32">
      <div className="mx-auto grid w-full max-w-7xl items-center gap-14 px-4 sm:px-6 lg:grid-cols-2 lg:gap-20 lg:px-8">
        <div>
          <p className="font-mono text-xs font-medium uppercase tracking-[0.18em] text-accent">
            The X-GEO method
          </p>
          <h2 ref={headlineRef} className="mt-4 font-heading text-display text-foreground">
            One query. Ten runs. Zero ambiguity.
          </h2>
          <p className="mt-5 max-w-lg text-body-lg text-muted-foreground">
            Commercial tools check once. We sample N=10 across temperature scales to compute
            real confidence intervals — so you know whether you actually moved, or just got lucky.
          </p>
          <ul ref={listRef} className="mt-8 space-y-3">
            {BULLETS.map((item) => (
              <li key={item} data-reveal className="flex items-center gap-3 text-body text-foreground/90">
                <span className="grid size-6 shrink-0 place-items-center rounded-md bg-accent/12 text-accent">
                  <CheckCircle2 className="size-3.5" />
                </span>
                {item}
              </li>
            ))}
          </ul>
        </div>

        <div className="rounded-2xl border border-border bg-card p-6 shadow-card">
          <div className="flex flex-wrap items-baseline justify-between gap-3">
            <div>
              <p className="text-sm font-medium text-foreground">
                “Does the Acme API support webhooks?”
              </p>
              <p className="mt-1 text-xs text-muted-foreground">ChatGPT Search · n=10 · this week</p>
            </div>
            <div className="text-right" style={{ opacity: 0.25 + bandT * 0.75 }}>
              <p className="font-heading text-2xl font-semibold text-foreground">CPI 0.62</p>
              <p className="font-mono text-xs text-accent">[0.57, 0.67]</p>
            </div>
          </div>

          <div className="mt-6 h-[300px] w-full" aria-hidden="true">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart margin={{ top: 8, right: 16, bottom: 4, left: -14 }}>
                <CartesianGrid stroke="hsl(var(--border))" strokeDasharray="3 5" vertical={false} />
                <XAxis
                  dataKey="run"
                  type="number"
                  domain={[1, 10]}
                  tickCount={10}
                  tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11, fontFamily: "Geist Mono, monospace" }}
                  tickLine={false}
                  axisLine={{ stroke: "hsl(var(--border))" }}
                  tickFormatter={(v: number) => `#${v}`}
                />
                <YAxis
                  domain={[0.4, 0.8]}
                  tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11, fontFamily: "Geist Mono, monospace" }}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(v: number) => v.toFixed(2)}
                />
                <ReferenceArea
                  y1={STOCHASTIC_MEAN - STOCHASTIC_BAND}
                  y2={STOCHASTIC_MEAN + STOCHASTIC_BAND}
                  fill="hsl(var(--accent))"
                  fillOpacity={0.1 * bandT}
                  stroke="hsl(var(--accent))"
                  strokeOpacity={0.25 * bandT}
                  strokeDasharray="4 4"
                />
                <ReferenceLine
                  y={STOCHASTIC_MEAN}
                  stroke="hsl(var(--accent))"
                  strokeDasharray="6 4"
                  strokeWidth={1.5}
                  strokeOpacity={0.15 + bandT * 0.85}
                />
                <Scatter
                  data={visible}
                  dataKey="probability"
                  fill="hsl(var(--accent))"
                  isAnimationActive={false}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>

          <div className="mt-4 flex items-center justify-between border-t border-border pt-4 font-mono text-[11px] text-muted-foreground">
            <span>p̂ = {STOCHASTIC_MEAN.toFixed(2)}</span>
            <span>σ = 0.029</span>
            <span>wilson(0.95) → ±{STOCHASTIC_BAND.toFixed(2)}</span>
          </div>
        </div>
      </div>
    </section>
  );
}
