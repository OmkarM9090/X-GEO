import { useRef } from "react";
import { Check, Minus, X } from "lucide-react";
import { gsap, useGSAP, MOTION_OK, ScrollTrigger } from "@/lib/gsap-config";
import { SectionHeading } from "@/components/shared/SectionHeading";
import { cn } from "@/lib/utils";

const COLUMNS = ["X-GEO", "Semrush", "Otterly.ai", "Manual audit"] as const;
const ROWS = [
  { label: "Stochastic multi-sampling", values: [true, false, false, false] },
  { label: "NLI factuality check", values: [true, false, false, false] },
  { label: "Local RAG simulation", values: [true, false, false, false] },
  { label: "Surgical patches under 5% edit", values: [true, false, false, false] },
  { label: "Confidence intervals", values: [true, false, false, false] },
] as const;

function Capability({ available, featured }: { available: boolean; featured: boolean }) {
  if (available) {
    return (
      <span
        data-compare-check
        className={cn(
          "inline-grid size-7 place-items-center rounded-full",
          featured ? "bg-accent/15 text-accent" : "bg-success/10 text-success",
        )}
        aria-label="Included"
      >
        <Check className="size-4" strokeWidth={2.5} />
      </span>
    );
  }

  return (
    <span className="inline-grid size-7 place-items-center rounded-full text-muted-foreground/35" aria-label="Not included">
      <X className="size-3.5" strokeWidth={1.8} />
    </span>
  );
}

/** Compact comparison matrix, with verified X-GEO capabilities emphasized. */
export function ComparisonTable() {
  const tableRef = useRef<HTMLDivElement>(null);

  useGSAP(
    () => {
      const root = tableRef.current;
      if (!root) return undefined;
      const media = gsap.matchMedia();
      media.add(MOTION_OK, () => {
        const rows = gsap.utils.toArray<HTMLElement>(root.querySelectorAll("[data-comparison-row]"));
        const triggers: ScrollTrigger[] = [];
        rows.forEach((row) => {
          const checks = row.querySelectorAll<HTMLElement>("[data-compare-check]");
          if (!checks.length) return;
          gsap.set(checks, { willChange: "transform, opacity" });
          const timeline = gsap.timeline({
            scrollTrigger: { trigger: row, start: "top 88%", once: true },
            onComplete: () => {
              gsap.set(checks, { clearProps: "willChange" });
            },
          });
          timeline
            .fromTo(checks, { scale: 0, opacity: 0 }, { scale: 1.2, opacity: 1, duration: 0.22, stagger: 0.045, ease: "back.out(2)" })
            .to(checks, { scale: 1, duration: 0.12, stagger: 0.025, ease: "power2.out" }, "-=0.05");
          if (timeline.scrollTrigger) triggers.push(timeline.scrollTrigger);
        });
        return () => {
          triggers.forEach((trigger) => trigger.kill());
          gsap.set(root.querySelectorAll("[data-compare-check]"), { clearProps: "transform,opacity,willChange" });
        };
      });
      return () => media.revert();
    },
    { scope: tableRef },
  );

  return (
    <section className="px-4 py-24 sm:px-6 md:py-32 lg:px-8">
      <div className="mx-auto w-full max-w-6xl">
        <SectionHeading
          eyebrow="A different class of measurement"
          title="How X-GEO compares"
          description="A point-in-time visibility check can’t answer a probability question. Compare the full measurement workflow."
          align="center"
          size="display"
        />

        <div ref={tableRef} className="mt-12 overflow-hidden rounded-2xl border border-border bg-card shadow-card">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[650px] border-separate border-spacing-0 text-left">
              <caption className="sr-only">Feature comparison between X-GEO, Semrush, Otterly.ai, and a manual audit process.</caption>
              <thead>
                <tr className="text-xs">
                  <th scope="col" className="sticky left-0 z-10 min-w-[225px] border-b border-border bg-card px-5 py-5 font-medium text-muted-foreground sm:px-7">Capability</th>
                  {COLUMNS.map((column, index) => (
                    <th
                      scope="col"
                      key={column}
                      className={cn(
                        "min-w-[108px] border-b border-border px-3 py-5 text-center font-medium sm:px-5",
                        index === 0 ? "border-x border-x-accent/35 bg-accent/[0.07] text-foreground" : "text-muted-foreground",
                      )}
                    >
                      {column}
                      {index === 0 && <span className="mx-auto mt-1 block h-px w-8 bg-accent/70" />}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {ROWS.map((row, rowIndex) => (
                  <tr key={row.label} data-comparison-row className="group">
                    <th
                      scope="row"
                      className="sticky left-0 z-10 border-b border-border/70 bg-card px-5 py-4 text-sm font-medium text-foreground/85 sm:px-7"
                    >
                      <span className="flex items-center gap-3">
                        <span className="font-mono text-[10px] text-muted-foreground/50">0{rowIndex + 1}</span>
                        {row.label}
                      </span>
                    </th>
                    {row.values.map((available, columnIndex) => (
                      <td
                        key={`${row.label}-${COLUMNS[columnIndex]}`}
                        className={cn(
                          "border-b border-border/70 px-3 py-3.5 text-center sm:px-5",
                          columnIndex === 0 && "border-x border-x-accent/35 bg-accent/[0.035]",
                        )}
                      >
                        <span className="inline-flex justify-center">
                          <Capability available={available} featured={columnIndex === 0} />
                        </span>
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="flex items-start gap-2.5 border-t border-border/70 px-5 py-4 text-xs leading-relaxed text-muted-foreground sm:px-7">
            <Minus className="mt-0.5 size-3.5 shrink-0" />
            <p>Competitor workflows vary by plan and configuration. This matrix focuses on the native, repeatable measurement loop shown here; human teams can of course perform additional analysis.</p>
          </div>
        </div>
      </div>
    </section>
  );
}
