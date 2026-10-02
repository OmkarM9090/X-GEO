import { useRef } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, CheckCircle2, ShieldCheck } from "lucide-react";
import { gsap, useGSAP, MOTION_OK } from "@/lib/gsap";
import { useSplitText } from "@/hooks/useSplitText";
import { useReveal } from "@/hooks/useScrollTrigger";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const SOV_BARS = [
  { name: "Acme Docs", value: 0.62, accent: true },
  { name: "Nortide", value: 0.48, accent: false },
  { name: "Vektor Labs", value: 0.31, accent: false },
];

const DIFF_LINES = [
  { type: "ctx", text: "Configure the webhook endpoint:" },
  { type: "del", text: "Requests time out after 5 seconds." },
  { type: "add", text: "Requests time out after 30s by default;" },
  { type: "add", text: "raise via `timeout_ms` (max 120s)." },
  { type: "ctx", text: "Retries use exponential backoff." },
];

function TileShell({
  children,
  title,
  description,
  wide,
}: {
  children: React.ReactNode;
  title: string;
  description: string;
  wide?: boolean;
}) {
  return (
    <article
      data-bento
      className={cn(
        "group flex flex-col rounded-2xl border border-border bg-card p-6 transition-all duration-300",
        "hover:-translate-y-0.5 hover:border-accent/50 hover:shadow-card",
        wide && "md:col-span-2",
      )}
    >
      <h3 className="font-heading text-[17px] font-semibold tracking-[-0.01em] text-foreground">
        {title}
      </h3>
      <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{description}</p>
      <div className="relative mt-6 flex flex-1 items-center justify-center overflow-hidden rounded-xl border border-border/70 bg-background/40 min-h-[168px]">
        {children}
      </div>
    </article>
  );
}

/** 1 — Monte Carlo CPI (wide): draw-on trend path with dotted band. */
function CpiVisual() {
  return (
    <svg viewBox="0 0 520 160" className="h-full w-full p-4" aria-hidden="true">
      <path data-cpi-band d="M16,58 C90,50 140,56 210,44 C280,32 340,40 420,26 C460,18 490,18 504,16" fill="none" stroke="hsl(var(--accent-glow))" strokeOpacity="0.35" strokeDasharray="3 5" strokeWidth="1.5" />
      <path data-cpi-band d="M16,102 C90,96 140,102 210,90 C280,78 340,86 420,72 C460,64 490,64 504,62" fill="none" stroke="hsl(var(--accent-glow))" strokeOpacity="0.35" strokeDasharray="3 5" strokeWidth="1.5" />
      <path
        data-cpi-path
        d="M16,80 C90,72 140,79 210,67 C280,55 340,63 420,49 C460,41 490,41 504,39"
        fill="none"
        stroke="hsl(var(--accent))"
        strokeWidth="2.5"
        strokeLinecap="round"
      />
      {[90, 210, 330, 450].map((x, i) => (
        <circle key={i} cx={x} cy={[71, 67, 59, 45][i]} r="3.5" fill="hsl(var(--accent))" />
      ))}
      <text x="16" y="146" fontSize="10" fontFamily="Geist Mono, monospace" className="fill-muted-foreground">W01</text>
      <text x="478" y="146" fontSize="10" fontFamily="Geist Mono, monospace" className="fill-muted-foreground">W12</text>
    </svg>
  );
}

/** 2 — NLI Factuality Guard: pulsing shield over verified claims. */
function NliVisual() {
  return (
    <div className="flex h-full w-full flex-col justify-center gap-2 p-5">
      <div className="relative mx-auto mb-3 grid size-12 place-items-center">
        <span className="absolute size-10 rounded-full border border-accent/40 animate-pulse-ring" />
        <span className="grid size-12 place-items-center rounded-full border border-accent/30 bg-accent/10">
          <ShieldCheck className="size-5 text-accent" />
        </span>
      </div>
      {[
        { claim: "timeout_ms default = 30s", score: "0.97" },
        { claim: "max payload = 256 KB", score: "0.94" },
      ].map((row) => (
        <div key={row.claim} className="flex items-center justify-between rounded-lg border border-border/70 bg-card px-3 py-2">
          <span className="flex items-center gap-2 font-mono text-[11px] text-foreground/80">
            <CheckCircle2 className="size-3.5 text-success" />
            {row.claim}
          </span>
          <span className="font-mono text-[10px] text-success">{row.score}</span>
        </div>
      ))}
    </div>
  );
}

/** 3 — Local RAG simulator: retrieval graph with flowing edges. */
function RagVisual() {
  const edges = [
    "M86,32 C120,32 130,66 164,72", "M86,66 C120,66 130,70 164,73",
    "M86,100 C120,100 130,76 164,75", "M86,32 C120,32 150,96 184,104",
    "M226,76 C260,74 280,62 314,60", "M246,104 C270,100 290,72 314,62",
  ];
  return (
    <svg viewBox="0 0 400 136" className="h-full w-full p-4" aria-hidden="true">
      {edges.map((d, i) => (
        <path key={i} d={d} fill="none" stroke="hsl(var(--accent) / 0.4)" strokeWidth="1.5" strokeDasharray="4 4" className="animate-dash-flow" />
      ))}
      {[{ y: 24, t: "doc#a" }, { y: 58, t: "doc#b" }, { y: 92, t: "doc#c" }].map((n) => (
        <g key={n.t}>
          <rect x="16" y={n.y} width="70" height="16" rx="5" fill="hsl(var(--muted))" stroke="hsl(var(--border))" />
          <text x="26" y={n.y + 11.5} fontSize="9.5" fontFamily="Geist Mono, monospace" className="fill-foreground/80">{n.t}</text>
        </g>
      ))}
      <rect x="164" y="64" width="62" height="20" rx="6" fill="hsl(var(--accent) / 0.15)" stroke="hsl(var(--accent) / 0.5)" />
      <text x="176" y="77" fontSize="9.5" fontFamily="Geist Mono, monospace" className="fill-accent">bm25</text>
      <rect x="184" y="96" width="62" height="20" rx="6" fill="hsl(var(--accent) / 0.15)" stroke="hsl(var(--accent) / 0.5)" />
      <text x="197" y="109" fontSize="9.5" fontFamily="Geist Mono, monospace" className="fill-accent">vector</text>
      <rect x="314" y="50" width="70" height="22" rx="6" fill="hsl(var(--accent))" />
      <text x="333" y="64.5" fontSize="9.5" fontFamily="Geist Mono, monospace" className="fill-accent-foreground">answer</text>
    </svg>
  );
}

/** 4 — Surgical patches: scoped code diff. */
function PatchVisual() {
  return (
    <div className="h-full w-full p-4 font-mono text-[11px] leading-[1.9]">
      <p className="mb-1 text-muted-foreground">docs/api/webhooks.md · chunk 41</p>
      {DIFF_LINES.map((line, i) => (
        <div
          key={i}
          className={cn(
            "flex gap-2 rounded px-2",
            line.type === "del" && "bg-danger/10 text-danger",
            line.type === "add" && "bg-success/10 text-success",
            line.type === "ctx" && "text-muted-foreground",
          )}
        >
          <span className="select-none opacity-60">
            {line.type === "del" ? "−" : line.type === "add" ? "+" : " "}
          </span>
          <span className="truncate">{line.text}</span>
        </div>
      ))}
    </div>
  );
}

/** 5 — Share of voice (wide): transform-only bar animation. */
function SovVisual() {
  return (
    <div className="flex h-full w-full flex-col justify-center gap-4 p-6">
      {SOV_BARS.map((bar) => (
        <div key={bar.name} className="flex items-center gap-4">
          <span className="w-24 shrink-0 text-xs text-muted-foreground">{bar.name}</span>
          <div className="relative h-2.5 flex-1 overflow-hidden rounded-full bg-muted/60">
            <div
              data-sov-fill
              className={cn("absolute inset-y-0 left-0 w-full origin-left rounded-full", bar.accent ? "bg-accent" : "bg-muted-foreground/40")}
              style={{ transform: `scaleX(${bar.value})` }}
            />
          </div>
          <span className={cn("w-10 shrink-0 text-right font-mono text-xs", bar.accent ? "text-accent" : "text-muted-foreground")}>
            {bar.value.toFixed(2)}
          </span>
        </div>
      ))}
      <p className="mt-1 font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
        topic: “api key management” · 3 engines · trailing 28 days
      </p>
    </div>
  );
}

/** 6 — Confidence bounds: gauge with animated needle. */
function BoundsVisual() {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-1 p-4">
      <svg viewBox="0 0 200 112" className="w-40" aria-hidden="true">
        <path d="M20,100 A80,80 0 0 1 180,100" fill="none" stroke="hsl(var(--muted))" strokeWidth="10" strokeLinecap="round" />
        <path
          d="M20,100 A80,80 0 0 1 180,100"
          fill="none"
          stroke="hsl(var(--accent) / 0.35)"
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray="125.6 251.2"
          strokeDashoffset="-63"
        />
        <g data-needle style={{ transform: "rotate(21.6deg)", transformOrigin: "100px 100px" }}>
          <line x1="100" y1="100" x2="100" y2="34" stroke="hsl(var(--accent))" strokeWidth="2.5" strokeLinecap="round" />
          <circle cx="100" cy="100" r="5" fill="hsl(var(--accent))" />
        </g>
      </svg>
      <p className="font-mono text-sm text-foreground">
        0.62 <span className="text-accent">± 0.05</span>
      </p>
      <p className="text-[11px] text-muted-foreground">significant at p &lt; 0.05</p>
    </div>
  );
}

export function FeatureBento() {
  const sectionRef = useReveal<HTMLElement>({
    selector: "[data-bento]",
    scale: 0.92,
    y: 24,
    stagger: 0.09,
    start: "top 78%",
  });
  const headlineRef = useSplitText<HTMLHeadingElement>({ kind: "lines" });
  const animScope = useRef<HTMLDivElement>(null);

  useGSAP(
    () => {
      const mm = gsap.matchMedia();
      mm.add(MOTION_OK, () => {
        const scope = animScope.current;
        if (!scope) return undefined;

        const tweens: gsap.core.Tween[] = [];

        scope.querySelectorAll<SVGPathElement>("[data-cpi-path]").forEach((path) => {
          const len = path.getTotalLength();
          gsap.set(path, { strokeDasharray: len, strokeDashoffset: len });
          tweens.push(
            gsap.to(path, {
              strokeDashoffset: 0,
              duration: 1.6,
              ease: "power2.out",
              scrollTrigger: { trigger: path, start: "top 85%", once: true },
            }),
          );
        });
        scope.querySelectorAll<SVGPathElement>("[data-cpi-band]").forEach((path) => {
          tweens.push(
            gsap.from(path, {
              opacity: 0,
              duration: 1,
              delay: 0.5,
              scrollTrigger: { trigger: path, start: "top 85%", once: true },
            }),
          );
        });
        scope.querySelectorAll<HTMLElement>("[data-sov-fill]").forEach((fill) => {
          tweens.push(
            gsap.from(fill, {
              scaleX: 0,
              duration: 1.1,
              ease: "power3.out",
              scrollTrigger: { trigger: fill, start: "top 88%", once: true },
            }),
          );
        });
        scope.querySelectorAll<SVGGElement>("[data-needle]").forEach((needle) => {
          tweens.push(
            gsap.from(needle, {
              rotation: -90,
              svgOrigin: "100 100",
              duration: 1.4,
              ease: "elastic.out(1, 0.5)",
              scrollTrigger: { trigger: needle, start: "top 88%", once: true },
            }),
          );
        });

        return () => tweens.forEach((t) => {
          t.scrollTrigger?.kill();
          t.kill();
        });
      });
      return () => mm.revert();
    },
    { scope: animScope },
  );

  return (
    <section id="features" ref={sectionRef} className="py-24 md:py-32">
      <div className="mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8" ref={animScope}>
        <div className="mx-auto max-w-2xl text-center">
          <p className="font-mono text-xs font-medium uppercase tracking-[0.18em] text-accent">
            Platform
          </p>
          <h2 ref={headlineRef} className="mt-4 font-heading text-display text-foreground">
            Everything you need to win AI search.
          </h2>
          <p className="mt-5 text-body-lg text-muted-foreground">
            Measurement, verification, and repair — one loop, closed every week.
          </p>
        </div>

        <div className="mt-16 grid grid-cols-1 gap-4 md:grid-cols-3">
          <TileShell
            wide
            title="Monte Carlo CPI tracking"
            description="Ten stratified runs per query, per engine. Wilson score bounds you can defend in a board meeting — not a screenshot of one lucky answer."
          >
            <CpiVisual />
          </TileShell>

          <TileShell
            title="NLI Factuality Guard"
            description="Every extracted claim is verified against your source corpus with NLI entailment before it can be recommended."
          >
            <NliVisual />
          </TileShell>

          <TileShell
            title="Local RAG simulator"
            description="We rebuild each engine’s retrieval stack locally — BM25 fused with vector search — so fixes are tested before they ship."
          >
            <RagVisual />
          </TileShell>

          <TileShell
            title="Surgical patches"
            description="Localized, chunk-level copy repairs. Accept a diff, push it to your CMS, and measure lift on the next sampling run."
          >
            <PatchVisual />
          </TileShell>

          <TileShell
            title="Confidence bounds"
            description="Every metric ships with an interval. If a change isn’t statistically significant, we say so."
          >
            <BoundsVisual />
          </TileShell>

          <TileShell
            wide
            title="Share of voice"
            description="Citation share across engines, topics, and locales. Watch a competitor’s patch land in your trend line the week it happens."
          >
            <SovVisual />
          </TileShell>

          <article
            data-bento
            className="flex flex-col justify-between rounded-2xl border border-accent/30 bg-gradient-to-br from-accent/[0.12] via-card to-card p-6 transition-all duration-300 hover:-translate-y-0.5 hover:border-accent/60 hover:shadow-glow-sm"
          >
            <div>
              <h3 className="font-heading text-[17px] font-semibold tracking-[-0.01em] text-foreground">
                Run your first audit
              </h3>
              <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">
                10 free Monte Carlo runs on your own content. Results in under an hour.
              </p>
            </div>
            <Button variant="accent" size="sm" asChild className="mt-6 w-fit">
              <Link to="/signup">
                Start free
                <ArrowRight className="size-3.5" />
              </Link>
            </Button>
          </article>
        </div>
      </div>
    </section>
  );
}
