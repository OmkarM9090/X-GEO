import { ArrowUpRight, FileText } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Navbar } from "@/components/marketing/Navbar";
import { Footer } from "@/components/marketing/Footer";
import { DOC_SECTIONS } from "@/data/faq";

function CodeBlock({ title, code }: { title: string; code: string }) {
  return (
    <div className="overflow-hidden rounded-xl border border-border">
      <div className="flex items-center gap-2 border-b border-white/10 bg-[#101014] px-4 py-2.5">
        <FileText className="size-3.5 text-white/40" />
        <span className="font-mono text-[11px] text-white/50">{title}</span>
      </div>
      <pre className="overflow-x-auto bg-[#0b0b10] p-4 font-mono text-[12px] leading-relaxed text-[#d7d7e3]">
        <code>{code}</code>
      </pre>
    </div>
  );
}

function Section({
  id,
  eyebrow,
  title,
  children,
}: {
  id: string;
  eyebrow: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section id={id} className="scroll-mt-28 border-b border-border/60 py-12 first:pt-0 last:border-b-0">
      <p className="font-mono text-[11px] font-medium uppercase tracking-[0.16em] text-accent">{eyebrow}</p>
      <h2 className="mt-3 font-heading text-h2 text-foreground">{title}</h2>
      <div className="mt-5 space-y-4 text-body text-muted-foreground">{children}</div>
    </section>
  );
}

const ENDPOINTS = [
  { method: "POST", path: "/v1/audits", note: "Create and queue an audit" },
  { method: "GET", path: "/v1/audits/{id}", note: "Poll status and CPI result" },
  { method: "GET", path: "/v1/audits/{id}/samples", note: "Raw per-run samples" },
  { method: "GET", path: "/v1/projects/{id}/trends", note: "Aggregated trend series" },
  { method: "POST", path: "/v1/webhooks", note: "Register drift / completion hooks" },
];

const META_LINKS = [
  { id: "changelog", label: "Changelog" },
  { id: "roadmap", label: "Roadmap" },
  { id: "status", label: "Status" },
  { id: "about", label: "About" },
  { id: "blog", label: "Blog" },
  { id: "careers", label: "Careers" },
  { id: "privacy", label: "Privacy" },
  { id: "terms", label: "Terms" },
  { id: "dpa", label: "DPA" },
  { id: "security", label: "Security" },
];

export default function DocsPage() {
  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="mx-auto w-full max-w-7xl px-4 pt-32 pb-24 sm:px-6 lg:px-8">
        <header className="max-w-2xl pb-12">
          <p className="font-mono text-xs font-medium uppercase tracking-[0.18em] text-accent">
            Documentation
          </p>
          <h1 className="mt-4 font-heading text-h1 text-foreground">
            Measure, verify, repair — through one API.
          </h1>
          <p className="mt-4 text-body-lg text-muted-foreground">
            Phase 1 covers core concepts and the sampling model. Hosted API access lands with
            the Phase 2 backend.
          </p>
        </header>

        <div className="grid gap-12 lg:grid-cols-[220px_1fr] lg:gap-16">
          {/* Sidebar */}
          <aside className="hidden self-start lg:sticky lg:top-24 lg:block">
            <nav aria-label="Documentation" className="space-y-7">
              {DOC_SECTIONS.map((section) => (
                <div key={section.group}>
                  <p className="text-xs font-semibold uppercase tracking-[0.14em] text-foreground">
                    {section.group}
                  </p>
                  <ul className="mt-3 space-y-2 border-l border-border">
                    {section.links.map((link) => (
                      <li key={link.label}>
                        <a
                          href={`/docs${link.href}`}
                          className="-ml-px block border-l border-transparent py-0.5 pl-4 text-sm text-muted-foreground transition-colors hover:border-accent hover:text-foreground"
                        >
                          {link.label}
                        </a>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </nav>
          </aside>

          {/* Article */}
          <article className="min-w-0">
            <Section id="introduction" eyebrow="Getting started" title="Introduction">
              <p>
                X-GEO measures how often AI search engines cite your brand when they answer
                the queries you care about. Because generative engines are stochastic, we never
                report a single observation: every metric is a{" "}
                <strong className="font-medium text-foreground">Citation Probability Interval (CPI)</strong>{" "}
                estimated from repeated Monte Carlo sampling, with NLI-based factuality
                verification layered on top.
              </p>
              <p>
                The loop is closed by <strong className="font-medium text-foreground">surgical patches</strong> —
                localized, chunk-level copy repairs whose lift is confirmed on the next sampling
                run, not assumed.
              </p>
            </Section>

            <Section id="quickstart" eyebrow="Getting started" title="Quickstart">
              <p>Three calls to your first interval:</p>
              <CodeBlock
                title="bash — create your first audit"
                code={`# 1. Create a project
curl -X POST https://api.xgeo.dev/v1/projects \\
  -H "Authorization: Bearer $XGEO_KEY" \\
  -d '{"name": "Acme Docs", "domain": "docs.acme.com"}'

# 2. Queue an audit (N=10 across temperatures 0.2–1.0)
curl -X POST https://api.xgeo.dev/v1/audits \\
  -H "Authorization: Bearer $XGEO_KEY" \\
  -d '{"project_id": "prj_8x2", "query": "does acme support webhooks",
       "engines": ["chatgpt", "aio", "perplexity"]}'

# 3. Read the interval
curl https://api.xgeo.dev/v1/audits/aud_94m \\
  -H "Authorization: Bearer $XGEO_KEY"
# → { "cpi": 0.62, "ci_95": [0.57, 0.67], "n": 10, "status": "completed" }`}
              />
            </Section>

            <Section id="authentication" eyebrow="Getting started" title="Authentication">
              <p>
                All requests authenticate with a Bearer API key scoped to a workspace. Keys are
                created in <span className="text-foreground">Settings → API access</span> and can be
                restricted to read-only or per-engine scopes.
              </p>
              <CodeBlock
                title="http — request headers"
                code={`Authorization: Bearer xgeo_sk_live_...
X-XGEO-Workspace: wsp_acme`}
              />
            </Section>

            <Section id="cpi" eyebrow="Core concepts" title="Citation Probability Interval">
              <p>
                For a query <em>q</em> and engine <em>e</em>, the citation probability p̂ is the share of
                sampled runs in which your brand is cited in the generated answer. The reported
                interval is a 95% Wilson score interval — stable at small N and never outside
                [0, 1]:
              </p>
              <CodeBlock
                title="wilson(0.95)"
                code={`center = (p̂ + z²/2n) / (1 + z²/n)
half   = z·√( p̂(1−p̂)/n + z²/4n² ) / (1 + z²/n)

n = 10, z = 1.96   →   p̂ = 0.62  ⇒  CI = [0.57, 0.67]`}
              />
              <p>
                A CPI of 0.62 [0.57, 0.67] reads: “sampling this query ten times across
                temperatures, we expect the engine to cite you in roughly six out of ten
                answers, and the uncertainty around that estimate is ±5 points at 95%
                confidence.”
              </p>
            </Section>

            <Section id="sampling" eyebrow="Core concepts" title="Monte Carlo sampling">
              <p>
                Each audit runs <span className="font-mono text-sm text-foreground">N=10</span> stratified
                samples across a temperature sweep (0.2 → 1.0) and persistent session seeds, so
                the spread you see is the engine’s intrinsic variance — not our noise. Pro plans
                can raise N to 25 for high-stakes queries, tightening bounds by roughly 40%.
              </p>
              <p>
                Drift alerts fire when a weekly CPI moves beyond ±3σ of its trailing eight-week
                baseline — the change is significant, not weather.
              </p>
            </Section>

            <Section id="nli" eyebrow="Core concepts" title="NLI verification">
              <p>
                Every claim an engine makes about you is classified against your crawled corpus
                as <span className="text-success">entailed</span>,{" "}
                <span className="text-danger">contradicted</span>, or{" "}
                <span className="text-warning">unsupported</span>. Flagged claims link to the exact
                source chunk that should have grounded them, with an entailment score per claim.
              </p>
            </Section>

            <Section id="patches" eyebrow="Core concepts" title="Surgical patches">
              <p>
                Patches are diffs scoped to a single retrieval chunk — tighten a definition,
                surface a limit, fix a stale default. Accepting a patch exports a diff for your
                CMS and schedules a confirmation audit; the lift report shows CPI before/after
                with overlapping-interval significance testing.
              </p>
            </Section>

            <Section id="api-audits" eyebrow="API reference" title="Endpoints">
              <div className="overflow-hidden rounded-xl border border-border">
                {ENDPOINTS.map((ep) => (
                  <div
                    key={ep.path}
                    className="flex flex-wrap items-center gap-3 border-b border-border/60 bg-card px-4 py-3 last:border-b-0"
                  >
                    <span className="w-12 font-mono text-[11px] font-semibold text-success">{ep.method}</span>
                    <span className="font-mono text-[12px] text-foreground">{ep.path}</span>
                    <span className="ml-auto text-xs text-muted-foreground">{ep.note}</span>
                  </div>
                ))}
              </div>
              <p id="api-projects" className="scroll-mt-28">
                <Badge variant="accent">Phase 2</Badge>{" "}
                <span className="ml-2">
                  Hosted endpoints activate when the sampling backend ships. The response
                  schemas above are frozen.
                </span>
              </p>
              <p id="api-webhooks" className="scroll-mt-28 sr-only">Webhooks</p>
            </Section>

            {/* Meta / legal stubs referenced from the footer */}
            <section className="py-12">
              <p className="font-mono text-[11px] font-medium uppercase tracking-[0.16em] text-accent">
                Index
              </p>
              <div className="mt-5 grid gap-3 sm:grid-cols-2">
                {META_LINKS.map((link) => (
                  <a
                    key={link.id}
                    id={link.id}
                    href={`/docs#${link.id}`}
                    className="group flex scroll-mt-28 items-center justify-between rounded-xl border border-border bg-card px-4 py-3.5 transition-colors hover:border-accent/40"
                  >
                    <span className="text-sm text-foreground/85">{link.label}</span>
                    <span className="flex items-center gap-2 text-xs text-muted-foreground">
                      Phase 2
                      <ArrowUpRight className="size-3.5 transition-transform duration-300 group-hover:-translate-y-0.5 group-hover:translate-x-0.5" />
                    </span>
                  </a>
                ))}
              </div>
            </section>
          </article>
        </div>
      </main>
      <Footer />
    </div>
  );
}
