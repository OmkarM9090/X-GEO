import { useRef, useState } from "react";
import { ArrowUpRight, Check, ChevronDown, CircleHelp, Command, Search } from "lucide-react";
import { gsap, useGSAP, MOTION_OK } from "@/lib/gsap-config";
import { SectionHeading } from "@/components/shared/SectionHeading";
import { SkeletonShimmer } from "@/components/animations/SkeletonShimmer";
import { cn } from "@/lib/utils";

const NAV_ITEMS = ["Overview", "Audits", "Citations", "Content", "Settings"];
const METRICS = [
  { label: "Citation probability", value: 62, suffix: "%", change: "+4.1pp", tone: "accent" },
  { label: "Verified claims", value: 94, suffix: "%", change: "+2.8pp", tone: "success" },
  { label: "Tracked prompts", value: 128, suffix: "", change: "+12", tone: "neutral" },
];

function ScrubDashboard() {
  const componentRef = useRef<HTMLDivElement>(null);
  const shimmerActiveRef = useRef(false);
  const [shimmerActive, setShimmerActive] = useState(false);
  const setShimmerStage = (active: boolean) => {
    if (shimmerActiveRef.current === active) return;
    shimmerActiveRef.current = active;
    setShimmerActive(active);
  };

  useGSAP(
    () => {
      const root = componentRef.current;
      const section = root?.closest<HTMLElement>("[data-dashboard-scrub-section]");
      if (!root || !section) return undefined;

      const media = gsap.matchMedia();
      media.add(`(min-width: 768px) and ${MOTION_OK}`, () => {
        const skeleton = root.querySelector<HTMLElement>("[data-scrub-skeleton]");
        const sidebar = root.querySelector<HTMLElement>("[data-scrub-sidebar]");
        const navItems = gsap.utils.toArray<HTMLElement>(root.querySelectorAll("[data-scrub-nav]"));
        const cards = gsap.utils.toArray<HTMLElement>(root.querySelectorAll("[data-scrub-metric]"));
        const chart = root.querySelector<HTMLElement>("[data-scrub-chart]");
        const path = root.querySelector<SVGPathElement>("[data-scrub-chart-path]");
        const confidence = root.querySelector<HTMLElement>("[data-scrub-confidence]");
        const glow = root.querySelector<HTMLElement>("[data-scrub-glow]");
        if (!skeleton || !sidebar || !chart || !path || !confidence || !glow) return undefined;

        const pathLength = path.getTotalLength();
        gsap.set(skeleton, { opacity: 1, willChange: "transform, opacity" });
        gsap.set(sidebar, { x: -16, opacity: 0, willChange: "transform, opacity" });
        gsap.set(navItems, { y: 8, opacity: 0, willChange: "transform, opacity" });
        gsap.set(cards, { y: 18, opacity: 0, willChange: "transform, opacity" });
        gsap.set(chart, { y: 12, opacity: 0, willChange: "transform, opacity" });
        gsap.set(path, { strokeDasharray: pathLength, strokeDashoffset: pathLength });
        gsap.set(confidence, { scale: 0.82, opacity: 0, willChange: "transform, opacity" });
        gsap.set(glow, { scale: 0.72, opacity: 0, willChange: "transform, opacity" });
        root.querySelectorAll<HTMLElement>("[data-scrub-count]").forEach((counter) => {
          counter.textContent = `0${counter.dataset.suffix ?? ""}`;
        });

        const countState = { progress: 0 };
        const timeline = gsap.timeline({
          defaults: { ease: "none" },
          scrollTrigger: {
            trigger: section,
            start: "top top",
            end: () => `+=${Math.round(window.innerHeight * 2)}`,
            scrub: 1,
            onEnter: () => setShimmerStage(true),
            onEnterBack: (self) => setShimmerStage(self.progress < 0.2),
            onUpdate: (self) => setShimmerStage(self.isActive && self.progress < 0.2),
            onLeave: () => setShimmerStage(false),
            onLeaveBack: () => setShimmerStage(false),
            pin: section,
            pinSpacing: true,
            anticipatePin: 1,
            invalidateOnRefresh: true,
          },
          onComplete: () => {
            gsap.set(root.querySelectorAll<HTMLElement>("[data-scrub-animated]"), { clearProps: "willChange" });
          },
        });

        timeline
          // 0–20%: empty frame + shimmer sweep.
          // 20–40%: the navigation arrives.
          .to(sidebar, { x: 0, opacity: 1, duration: 0.13 }, 0.22)
          .to(navItems, { y: 0, opacity: 1, duration: 0.12, stagger: 0.025 }, 0.27)
          // 40–60%: metric tiles and values build in.
          .to(cards, { y: 0, opacity: 1, duration: 0.15, stagger: 0.025 }, 0.43)
          .to(
            countState,
            {
              progress: 1,
              duration: 0.18,
              onUpdate: () => {
                root.querySelectorAll<HTMLElement>("[data-scrub-count]").forEach((counter, index) => {
                  const target = METRICS[index]?.value ?? 0;
                  counter.textContent = `${Math.round(target * countState.progress)}${counter.dataset.suffix ?? ""}`;
                });
              },
            },
            0.44,
          )
          // 60–80%: chart and interval line draw.
          .to(chart, { y: 0, opacity: 1, duration: 0.11 }, 0.62)
          .to(path, { strokeDashoffset: 0, duration: 0.17 }, 0.63)
          // 80–100%: confidence badge resolves, then the pin releases.
          .to(glow, { scale: 1.1, opacity: 0.48, duration: 0.12 }, 0.82)
          .to(confidence, { scale: 1, opacity: 1, duration: 0.12 }, 0.83)
          .to(confidence, { scale: 1.035, duration: 0.05, yoyo: true, repeat: 1, ease: "power1.inOut" }, 0.9);

        return () => {
          timeline.scrollTrigger?.kill();
          timeline.kill();
          gsap.set(root.querySelectorAll<HTMLElement>("[data-scrub-animated]"), { clearProps: "transform,opacity,willChange" });
          gsap.set(path, { clearProps: "strokeDasharray,strokeDashoffset" });
        };
      });

      media.add(`(max-width: 767px) and ${MOTION_OK}`, () => {
        setShimmerStage(false);
        const mobileItems = gsap.utils.toArray<HTMLElement>(root.querySelectorAll("[data-scrub-mobile-reveal]"));
        gsap.from(mobileItems, {
          y: 14,
          opacity: 0,
          duration: 0.55,
          stagger: 0.08,
          ease: "power3.out",
          clearProps: "willChange",
          scrollTrigger: { trigger: section, start: "top 78%", once: true },
        });
      });
      media.add("(prefers-reduced-motion: reduce)", () => {
        setShimmerStage(false);
      });

      return () => media.revert();
    },
    { scope: componentRef },
  );

  return (
    <div
      ref={componentRef}
      data-cursor="view"
      className="relative mx-auto w-full max-w-6xl overflow-hidden rounded-2xl border border-border bg-[#0d0d11] shadow-[0_38px_120px_-45px_rgba(0,0,0,0.8)]"
    >
      <div className="flex h-11 items-center gap-3 border-b border-white/[0.07] bg-[#111116] px-4 sm:px-5">
        <div className="flex gap-1.5" aria-hidden="true">
          <span className="size-2 rounded-full bg-[#ff5f57]" />
          <span className="size-2 rounded-full bg-[#febc2e]" />
          <span className="size-2 rounded-full bg-[#28c840]" />
        </div>
        <div className="mx-auto flex h-6 w-[min(54%,400px)] items-center justify-center gap-2 rounded-md border border-white/[0.06] bg-black/20 px-3 text-[10px] text-white/35">
          <span className="size-1.5 rounded-full bg-emerald-400" /> app.x-geo.dev / overview
        </div>
        <span className="hidden items-center gap-1 text-[10px] text-white/35 sm:inline-flex"><Command className="size-3" /> K</span>
      </div>

      <div className="relative grid min-h-[360px] grid-cols-1 sm:min-h-[380px] sm:grid-cols-[148px_minmax(0,1fr)] md:min-h-[420px] md:grid-cols-[180px_minmax(0,1fr)]">
        <aside data-scrub-sidebar data-scrub-animated className="hidden border-r border-white/[0.07] bg-[#101015] p-4 sm:block">
          <div className="flex items-center gap-2.5 px-1 pb-6 pt-1">
            <span className="grid size-7 place-items-center rounded-lg bg-violet-400/15 text-violet-300">
              <span className="font-heading text-sm font-bold">X</span>
            </span>
            <span className="font-heading text-[12px] font-semibold text-white/80">Acme Studio</span>
            <ChevronDown className="ml-auto size-3 text-white/30" />
          </div>
          <nav aria-label="Dashboard preview navigation" className="space-y-1">
            {NAV_ITEMS.map((item, index) => (
              <div
                key={item}
                data-scrub-nav
                data-scrub-animated
                className={cn(
                  "flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-[11px] text-white/45",
                  index === 0 && "bg-white/[0.07] text-white/85",
                )}
              >
                <span className={cn("size-1.5 rounded-full", index === 0 ? "bg-violet-300" : "bg-white/20")} />
                {item}
                {item === "Audits" && <span className="ml-auto rounded bg-white/[0.08] px-1.5 py-0.5 font-mono text-[9px] text-white/45">12</span>}
              </div>
            ))}
          </nav>
          <div className="mt-8 rounded-lg border border-white/[0.07] bg-white/[0.025] p-3">
            <div className="flex items-center gap-2 text-[10px] text-white/40"><CircleHelp className="size-3" /> Need a hand?</div>
            <div className="mt-2 h-1 w-full rounded bg-white/[0.07]"><span className="block h-full w-[62%] rounded bg-violet-400/80" /></div>
          </div>
        </aside>

        <div className="min-w-0 bg-[#0d0d11] p-4 sm:p-5 md:p-7">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="font-mono text-[9px] uppercase tracking-[0.15em] text-white/35">Workspace / Overview</p>
              <h3 className="mt-1.5 font-heading text-lg font-semibold tracking-[-0.03em] text-white/90 md:text-xl">Good morning, Alex</h3>
              <p className="mt-1 text-[10px] text-white/35">Your AI search visibility, at a glance.</p>
            </div>
            <div className="hidden items-center gap-2 rounded-lg border border-white/[0.07] bg-white/[0.025] px-3 py-2 text-[10px] text-white/40 sm:flex">
              <Search className="size-3" /> Search queries <kbd className="ml-3 rounded border border-white/10 px-1 py-0.5 font-mono">⌘ K</kbd>
            </div>
          </div>

          <div className="mt-5 grid grid-cols-2 gap-2.5 md:grid-cols-3 md:gap-3">
            {METRICS.map((metric, index) => (
              <article key={metric.label} data-scrub-metric data-scrub-animated data-scrub-mobile-reveal className={cn("rounded-xl border border-white/[0.07] bg-[#121218] p-3.5 sm:p-4", index === 2 && "hidden md:block")}>
                <div className="flex items-center justify-between gap-2">
                  <p className="truncate text-[9px] text-white/40 sm:text-[10px]">{metric.label}</p>
                  <ArrowUpRight className={cn("size-3 shrink-0", metric.tone === "success" ? "text-emerald-300" : "text-violet-300")} />
                </div>
                <div className="mt-3 flex items-baseline gap-2">
                  <p className="font-mono text-[23px] font-medium tracking-[-0.06em] text-white/90 sm:text-[27px]">
                    <span data-scrub-count data-suffix={metric.suffix}>{metric.value}{metric.suffix}</span>
                  </p>
                  <span className="hidden font-mono text-[9px] text-emerald-300/80 sm:inline">{metric.change}</span>
                </div>
                <p className="mt-1 text-[9px] text-white/25">vs. previous 28 days</p>
              </article>
            ))}
          </div>

          <div className="mt-3 grid gap-3 lg:grid-cols-[1.35fr_0.9fr]">
            <section data-scrub-chart data-scrub-animated data-scrub-mobile-reveal className="rounded-xl border border-white/[0.07] bg-[#121218] p-3.5 sm:p-4">
              <div className="flex items-start justify-between gap-3">
                <div><p className="text-[10px] font-medium text-white/70">Citation probability</p><p className="mt-1 text-[9px] text-white/30">All tracked engines · last 12 weeks</p></div>
                <span className="inline-flex items-center gap-1.5 rounded-md border border-white/[0.07] px-2 py-1 text-[9px] text-white/40">12 weeks <ChevronDown className="size-2.5" /></span>
              </div>
              <svg viewBox="0 0 520 140" className="mt-3 h-[104px] w-full sm:h-[124px]" role="img" aria-label="Citation probability trend rising over twelve weeks">
                {[25, 58, 91, 124].map((y) => <line key={y} x1="0" x2="520" y1={y} y2={y} stroke="rgba(255,255,255,.08)" strokeDasharray="2 5" />)}
                <path d="M8 111 C48 106 68 92 104 96 S168 77 201 84 S263 59 300 67 S365 44 398 51 S463 24 512 31" fill="none" stroke="rgba(167,139,250,.12)" strokeWidth="14" strokeLinecap="round" />
                <path data-scrub-chart-path d="M8 111 C48 106 68 92 104 96 S168 77 201 84 S263 59 300 67 S365 44 398 51 S463 24 512 31" fill="none" stroke="#a78bfa" strokeWidth="2.4" strokeLinecap="round" />
                <circle cx="512" cy="31" r="4" fill="#c4b5fd" />
              </svg>
              <div className="mt-1 flex justify-between font-mono text-[8px] text-white/25"><span>W01</span><span>W06</span><span>W12</span></div>
            </section>

            <section data-scrub-mobile-reveal className="hidden rounded-xl border border-white/[0.07] bg-[#121218] p-4 lg:block">
              <div className="flex items-center justify-between"><p className="text-[10px] font-medium text-white/70">Latest audit</p><span className="inline-flex items-center gap-1 rounded-full bg-emerald-400/10 px-2 py-1 text-[8px] text-emerald-300"><Check className="size-2.5" /> verified</span></div>
              <p className="mt-5 text-[10px] leading-relaxed text-white/45">“Which platform offers the most reliable API observability?”</p>
              <div className="mt-4 border-t border-white/[0.07] pt-4"><p className="text-[9px] text-white/30">Citation Probability</p><p className="mt-1 font-mono text-2xl text-white/85">0.72 <span className="text-[10px] text-violet-300">[0.67, 0.77]</span></p></div>
              <div className="mt-3 flex items-center gap-2"><span className="size-1.5 rounded-full bg-violet-300" /><span className="text-[9px] text-white/40">ChatGPT Search</span><span className="ml-auto font-mono text-[9px] text-white/30">N=10</span></div>
            </section>
          </div>
        </div>

        <div data-scrub-skeleton className="pointer-events-none absolute inset-0 z-20 p-5 opacity-0 sm:p-7" aria-hidden="true">
          <SkeletonShimmer
            loading={shimmerActive}
            rounded="rounded-none"
            className="absolute inset-0 min-h-0 border-0 bg-transparent"
            skeletonClassName="rounded-none border-0 bg-[#0d0d11]"
            skeleton={(
              <div className="h-full min-h-[360px] p-5 sm:min-h-[380px] sm:p-7 md:min-h-[420px]" aria-hidden="true">
                <div className="h-3 w-24 rounded bg-white/[0.07]" />
                <div className="mt-3 h-5 w-48 rounded bg-white/[0.08]" />
                <div className="mt-6 grid grid-cols-3 gap-3">
                  {[0, 1, 2].map((item) => <div key={item} className="h-[92px] rounded-xl border border-white/[0.05] bg-white/[0.035]" />)}
                </div>
                <div className="mt-3 h-[150px] rounded-xl border border-white/[0.05] bg-white/[0.035]" />
              </div>
            )}
          />
        </div>
      </div>

      <div className="absolute bottom-4 right-4 z-30 sm:bottom-6 sm:right-6">
        <span data-scrub-glow className="pointer-events-none absolute inset-[-14px] rounded-full bg-violet-400/30 blur-xl" />
        <div data-scrub-confidence className="relative flex items-center gap-2 rounded-full border border-violet-300/35 bg-[#17121f] px-3 py-2 text-[10px] text-white shadow-[0_0_28px_rgba(167,139,250,.18)] sm:px-4 sm:py-2.5 sm:text-xs">
          <span className="size-1.5 rounded-full bg-violet-300 shadow-[0_0_10px_rgba(196,181,253,.8)]" />
          <span className="text-white/55">Citation Probability:</span>
          <strong className="font-mono font-medium text-white">72% <span className="text-violet-200">± 5%</span></strong>
        </div>
      </div>
    </div>
  );
}

export function DashboardScrub() {
  return (
    <section data-dashboard-scrub-section className="relative flex min-h-[100svh] flex-col justify-center px-4 pt-24 pb-10 sm:px-6 lg:px-8">
      <div className="mx-auto mb-6 w-full max-w-6xl md:mb-8">
        <SectionHeading
          eyebrow="From signal to action"
          title="See the whole measurement loop."
          description="A real-time view of sampling, verification, and confidence — assembled as you scroll."
          align="left"
          size="h2"
          className="max-w-2xl"
        />
      </div>
      <ScrubDashboard />
    </section>
  );
}
