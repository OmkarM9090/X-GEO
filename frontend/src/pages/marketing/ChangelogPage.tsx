import { Link } from "react-router-dom";
import { ArrowUpRight, Check, GitCommitHorizontal, Sparkles } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Navbar } from "@/components/marketing/Navbar";
import { Footer } from "@/components/marketing/Footer";
import { SectionHeading } from "@/components/shared/SectionHeading";

const RELEASES = [
  {
    date: "October 2, 2026",
    version: "v0.8.0",
    title: "Citation confidence, made visible",
    type: "Product",
    details: [
      "Added a new confidence interval view across all tracked queries.",
      "Improved source-level claim review with clearer evidence excerpts.",
      "Reduced visual noise in the workspace and tightened keyboard navigation.",
    ],
  },
  {
    date: "September 10, 2026",
    version: "v0.7.2",
    title: "A faster audit workspace",
    type: "Improvement",
    details: [
      "Audit results now appear in a more compact, scannable layout.",
      "Trend charts keep their scale when switching between engines.",
    ],
  },
  {
    date: "August 19, 2026",
    version: "v0.7.0",
    title: "Claim verification enters the loop",
    type: "Product",
    details: [
      "Added Natural Language Inference status for supported claims.",
      "Source chunks are linked directly from flagged statements.",
      "Exported results now preserve audit sample metadata.",
    ],
  },
  {
    date: "July 28, 2026",
    version: "v0.6.4",
    title: "Small fixes, more signal",
    type: "Fix",
    details: [
      "Improved empty states and more resilient form validation.",
      "Fixed a contrast issue in light theme and polished mobile tables.",
    ],
  },
];

const releaseVariant = (type: string) =>
  type === "Product" ? "accent" : type === "Fix" ? "success" : "default";

export default function ChangelogPage() {
  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="px-4 pb-24 pt-32 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-6xl">
          <SectionHeading
            eyebrow="Product updates"
            title="Changelog"
            description="What’s new in X-GEO. Thoughtful updates to how teams measure, verify, and improve their visibility in AI search."
            align="left"
            size="display"
            className="max-w-3xl"
          />

          <div className="relative mt-14 grid gap-8 lg:grid-cols-[180px_minmax(0,1fr)] lg:gap-12">
            <div className="hidden lg:block">
              <div className="sticky top-24 rounded-xl border border-border bg-card/60 p-4">
                <p className="font-mono text-[10px] uppercase tracking-[0.15em] text-muted-foreground">Release feed</p>
                <p className="mt-3 font-heading text-xl font-semibold text-foreground">2026</p>
                <p className="mt-1 text-xs text-muted-foreground">4 notable updates</p>
              </div>
            </div>
            <div className="space-y-4">
              {RELEASES.map((release, index) => (
                <article key={release.version} className="relative rounded-2xl border border-border bg-card p-6 shadow-card sm:p-8" data-cursor="interactive">
                  {index < RELEASES.length - 1 && <span aria-hidden="true" className="absolute -bottom-5 left-[-1.35rem] hidden h-6 w-px bg-border lg:block" />}
                  <div className="flex flex-wrap items-center gap-2.5">
                    <Badge variant={releaseVariant(release.type)}>{release.type}</Badge>
                    <span className="font-mono text-[11px] text-muted-foreground">{release.version}</span>
                    <span className="ml-auto text-xs text-muted-foreground">{release.date}</span>
                  </div>
                  <h2 className="mt-5 font-heading text-[21px] font-semibold tracking-[-0.025em] text-foreground sm:text-2xl">{release.title}</h2>
                  <ul className="mt-4 space-y-3">
                    {release.details.map((detail) => (
                      <li key={detail} className="flex items-start gap-3 text-sm leading-relaxed text-muted-foreground">
                        <Check className="mt-0.5 size-4 shrink-0 text-accent" />{detail}
                      </li>
                    ))}
                  </ul>
                  <div className="mt-6 flex flex-wrap items-center justify-between gap-3 border-t border-border/70 pt-4">
                    <span className="inline-flex items-center gap-2 text-[11px] text-muted-foreground"><GitCommitHorizontal className="size-3.5" /> Product update</span>
                    {index === 0 && <span className="inline-flex items-center gap-1.5 text-[11px] text-accent"><Sparkles className="size-3.5" /> Latest release</span>}
                  </div>
                </article>
              ))}
            </div>
          </div>

          <div className="mt-8 flex flex-col items-start justify-between gap-4 rounded-2xl border border-border bg-card/60 p-6 sm:flex-row sm:items-center sm:p-7">
            <div><p className="font-heading font-medium text-foreground">Need the implementation details?</p><p className="mt-1 text-sm text-muted-foreground">Read the measurement model and API overview in the documentation.</p></div>
            <Link to="/docs" className="inline-flex items-center gap-1.5 text-sm font-medium text-accent transition-colors hover:text-accent-glow">Open docs <ArrowUpRight className="size-4" /></Link>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
