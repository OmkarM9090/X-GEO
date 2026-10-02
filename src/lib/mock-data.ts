import {
  Aperture, Box, Circle, Compass, Dices, Database, Globe,
  Hexagon, Layers, ShieldCheck, Square, Triangle,
} from "lucide-react";
import type {
  AppNotification, Audit, BentoFeature, CitationSample, CommandItem,
  DashboardMetrics, DocSection, Engine, FAQItem, HowItWorksStep, LogoItem,
  PricingTier, Testimonial, TrendPoint,
} from "@/types";

/* ---------- Engines ---------- */

export const ENGINE_LABELS: Record<Engine, string> = {
  chatgpt: "ChatGPT Search",
  aio: "Google AIO",
  perplexity: "Perplexity",
};

/* ---------- Stochastic demo (USP) ---------- */

export const STOCHASTIC_MEAN = 0.62;
export const STOCHASTIC_BAND = 0.05;

export const STOCHASTIC_SAMPLES: CitationSample[] = [
  { run: 1, probability: 0.60, temperature: 0.2, cited: true },
  { run: 2, probability: 0.65, temperature: 0.3, cited: true },
  { run: 3, probability: 0.58, temperature: 0.4, cited: true },
  { run: 4, probability: 0.63, temperature: 0.5, cited: true },
  { run: 5, probability: 0.67, temperature: 0.55, cited: true },
  { run: 6, probability: 0.61, temperature: 0.6, cited: true },
  { run: 7, probability: 0.59, temperature: 0.7, cited: false },
  { run: 8, probability: 0.64, temperature: 0.8, cited: true },
  { run: 9, probability: 0.62, temperature: 0.9, cited: true },
  { run: 10, probability: 0.66, temperature: 1.0, cited: false },
];

/* ---------- Dashboard ---------- */

export const DASHBOARD_METRICS: DashboardMetrics = {
  avgCpi: { value: 0.62, delta: 0.041 },
  nliPrecision: { value: 0.943, delta: 0.007 },
  activeAudits: { value: 12, delta: 3 },
  monthlyRuns: { value: 1248, delta: 212, limit: 2000 },
};

export const RECENT_AUDITS: Audit[] = [
  { id: "A-1042", query: "best headless CMS for e-commerce teams", engine: "chatgpt", cpi: 0.71, lower: 0.65, upper: 0.77, delta: 0.06, status: "completed", runs: 10, updatedAt: "12 min ago" },
  { id: "A-1041", query: "acme vs nortide uptime SLA comparison", engine: "perplexity", cpi: 0.54, lower: 0.47, upper: 0.61, delta: -0.03, status: "completed", runs: 10, updatedAt: "44 min ago" },
  { id: "A-1040", query: "how to rotate API keys on Acme", engine: "aio", cpi: 0.83, lower: 0.78, upper: 0.88, delta: 0.11, status: "completed", runs: 10, updatedAt: "1 h ago" },
  { id: "A-1039", query: "SOC 2 compliant vector database vendors", engine: "chatgpt", cpi: 0.47, lower: 0.40, upper: 0.54, delta: 0.02, status: "running", runs: 7, updatedAt: "running" },
  { id: "A-1038", query: "enterprise pricing for Acme platform", engine: "perplexity", cpi: 0.66, lower: 0.60, upper: 0.72, delta: 0.04, status: "scheduled", runs: 0, updatedAt: "queued 18:00" },
];

export const TREND_DATA: TrendPoint[] = [
  { date: "W01", chatgpt: 0.45, aio: 0.38, perplexity: 0.41 },
  { date: "W02", chatgpt: 0.47, aio: 0.40, perplexity: 0.44 },
  { date: "W03", chatgpt: 0.44, aio: 0.42, perplexity: 0.43 },
  { date: "W04", chatgpt: 0.51, aio: 0.45, perplexity: 0.49 },
  { date: "W05", chatgpt: 0.53, aio: 0.44, perplexity: 0.52 },
  { date: "W06", chatgpt: 0.58, aio: 0.49, perplexity: 0.50 },
  { date: "W07", chatgpt: 0.57, aio: 0.53, perplexity: 0.55 },
  { date: "W08", chatgpt: 0.62, aio: 0.55, perplexity: 0.58 },
  { date: "W09", chatgpt: 0.61, aio: 0.57, perplexity: 0.62 },
  { date: "W10", chatgpt: 0.66, aio: 0.60, perplexity: 0.63 },
  { date: "W11", chatgpt: 0.69, aio: 0.63, perplexity: 0.65 },
  { date: "W12", chatgpt: 0.71, aio: 0.66, perplexity: 0.68 },
];

export const NOTIFICATIONS: AppNotification[] = [
  { id: "n1", title: "Audit A-1042 completed", description: "CPI 0.71 [0.65, 0.77] — up 6.0pp vs last week.", time: "12 min ago", unread: true, kind: "audit" },
  { id: "n2", title: "Citation drift detected", description: "Perplexity CPI dropped 3.2pp on “uptime SLA comparison”.", time: "44 min ago", unread: true, kind: "alert" },
  { id: "n3", title: "Weekly report ready", description: "Share of voice across 3 engines, 42 tracked queries.", time: "3 h ago", unread: false, kind: "report" },
];

export const COMMAND_ITEMS: CommandItem[] = [
  { id: "c1", label: "Go to Overview", hint: "G O", group: "Navigate" },
  { id: "c2", label: "Go to Projects", hint: "G P", group: "Navigate" },
  { id: "c3", label: "Go to Settings", hint: "G S", group: "Navigate" },
  { id: "c4", label: "Run new audit", hint: "⌘ R", group: "Actions" },
  { id: "c5", label: "Export citation data", hint: "CSV", group: "Actions" },
  { id: "c6", label: "A-1042 — headless CMS for e-commerce", hint: "0.71", group: "Audits" },
  { id: "c7", label: "A-1040 — rotate API keys on Acme", hint: "0.83", group: "Audits" },
];

/* ---------- Marketing ---------- */

export const LOGOS: LogoItem[] = [
  { name: "Nortide", Icon: Hexagon },
  { name: "Vektor Labs", Icon: Triangle },
  { name: "Loomfield", Icon: Square },
  { name: "Parsec", Icon: Circle },
  { name: "Helios Data", Icon: Aperture },
  { name: "Cairn Systems", Icon: Layers },
  { name: "Quanta", Icon: Box },
  { name: "Fjordline", Icon: Compass },
];

export const BENTO_FEATURES: BentoFeature[] = [
  {
    key: "cpi",
    title: "Monte Carlo CPI tracking",
    description:
      "Ten stratified runs per query, per engine. Wilson score bounds you can defend in a board meeting — not a screenshot of one lucky answer.",
    span: "wide",
  },
  {
    key: "nli",
    title: "NLI Factuality Guard",
    description:
      "Every extracted claim is verified against your source corpus with NLI entailment before it can be recommended.",
    span: "tile",
  },
  {
    key: "rag",
    title: "Local RAG simulator",
    description:
      "We rebuild each engine’s retrieval stack locally — BM25 fused with vector search — so fixes are tested before they ship.",
    span: "tile",
  },
  {
    key: "patches",
    title: "Surgical patches",
    description:
      "Localized, chunk-level copy repairs. Accept a diff, push it to your CMS, and measure lift on the next sampling run.",
    span: "tile",
  },
  {
    key: "sov",
    title: "Share of voice",
    description:
      "Citation share across engines, topics, and locales. Watch a competitor’s patch land in your trend line the week it happens.",
    span: "wide",
  },
  {
    key: "bounds",
    title: "Confidence bounds",
    description:
      "Every metric ships with an interval. If a change isn’t statistically significant, we say so.",
    span: "tile",
  },
];

export const HOW_IT_WORKS: HowItWorksStep[] = [
  {
    index: "01",
    title: "Crawl",
    description: "See what retrieval sees.",
    detail:
      "Hybrid static + dynamic crawling renders your docs, blog, and changelog exactly as an AI engine’s retriever ingests them — including JS-heavy pages.",
    Icon: Globe,
  },
  {
    index: "02",
    title: "Simulate",
    description: "Rebuild the pipeline locally.",
    detail:
      "We reconstruct each engine’s stack: BM25 keyword retrieval fused with pgvector semantic search, then re-ranking. Your content, scored the same way.",
    Icon: Database,
  },
  {
    index: "03",
    title: "Sample",
    description: "N=10, across temperatures.",
    detail:
      "Every query runs ten times across temperature settings 0.2–1.0. Variance that a single check hides becomes a measurable interval.",
    Icon: Dices,
  },
  {
    index: "04",
    title: "Verify & repair",
    description: "Fix the exact chunk that failed.",
    detail:
      "NLI entailment validates each claim against your corpus. Failed chunks receive surgical patches — with measured lift on re-runs.",
    Icon: ShieldCheck,
  },
];

export const PRICING_TIERS: PricingTier[] = [
  {
    name: "Free",
    price: 0,
    period: "forever",
    description: "For a first honest look at your AI visibility.",
    features: ["10 audits / month", "1 project", "3 engines, 1 locale", "7-day metric history", "Community support"],
    cta: "Start free",
    featured: false,
  },
  {
    name: "Pro",
    price: 79,
    period: "per month",
    description: "For content teams shipping weekly.",
    features: [
      "200 audits / month",
      "Unlimited projects",
      "All engines, 12 locales",
      "NLI Factuality Guard",
      "Surgical patch suggestions",
      "API + CSV export",
      "90-day metric history",
    ],
    cta: "Start 14-day trial",
    featured: true,
  },
  {
    name: "Agency",
    price: 249,
    period: "per month",
    description: "For teams managing many brands.",
    features: [
      "2,000 audits / month",
      "Client workspaces",
      "White-label reports",
      "Priority sampling queue",
      "BigQuery export",
      "Unlimited history",
    ],
    cta: "Talk to sales",
    featured: false,
  },
];

export const TESTIMONIALS: Testimonial[] = [
  {
    quote: "We replaced our weekly rank-check ritual with CPI dashboards. The variance data alone killed two bad content bets.",
    name: "Mara Jensen", role: "Head of Content Platform", company: "Nortide", initials: "MJ",
  },
  {
    quote: "First tool that told us a lift was not significant. That honesty changed how we report to the exec team.",
    name: "Devon Adewale", role: "SEO Director", company: "Vektor Labs", initials: "DA",
  },
  {
    quote: "The surgical patches are scoped to the chunk that actually failed retrieval. Our editors trust the diffs because they can see why.",
    name: "Priya Raman", role: "Editorial Manager", company: "Parsec", initials: "PR",
  },
  {
    quote: "N=10 sampling caught that our Perplexity visibility was pure noise week over week. A single checker would have called it a win.",
    name: "Tomás Herrera", role: "Technical Content Architect", company: "Helios Data", initials: "TH",
  },
  {
    quote: "We run X-GEO before every docs launch now. If the interval moves, we know the copy worked. If it doesn’t, we revert.",
    name: "Alina Kowalska", role: "Docs Lead", company: "Cairn Systems", initials: "AK",
  },
  {
    quote: "Share of voice across three engines in one view ended the screenshot wars in our marketing Slack.",
    name: "Ben Whitfield", role: "VP Growth", company: "Loomfield", initials: "BW",
  },
];

export const FAQ_ITEMS: FAQItem[] = [
  {
    question: "What is a Citation Probability Interval?",
    answer:
      "The probability that an AI engine cites your brand for a given query, expressed as a range — e.g. 0.62 [0.57, 0.67]. We compute it from repeated sampling, not one request, so the interval reflects the engine’s actual answer distribution. Bounds are Wilson score intervals at 95% confidence.",
  },
  {
    question: "Why N=10 samples per query?",
    answer:
      "Ten stratified runs across temperature settings 0.2–1.0 is the smallest sample that keeps the interval within roughly ±5–7 points for mid-range probabilities, at a defensible cost per query. Pro plans and above let you raise N for tighter bounds on high-stakes queries.",
  },
  {
    question: "How is this different from an AI rank tracker?",
    answer:
      "Rank trackers take one snapshot. Generative engines are stochastic: the same query ten minutes apart can flip a citation. A snapshot mistakes noise for signal — our customers have seen ±20 point swings within a day. We model the distribution; trackers photograph it once.",
  },
  {
    question: "What does the NLI Factuality Guard actually check?",
    answer:
      "For every claim an engine makes about you, we run natural-language inference against your crawled corpus: does a source chunk entail this claim, contradict it, or stay neutral? Contradicted and unsupported claims are flagged with the exact source chunk. Measured precision is 0.94 on our 2,400-claim evaluation set.",
  },
  {
    question: "Which AI engines do you support?",
    answer:
      "ChatGPT Search, Google AI Overviews, and Perplexity are generally available. Claude and Gemini sampling is in beta on Agency plans. Engine coverage is versioned, so you can see when a provider ships a model update that shifts your intervals.",
  },
  {
    question: "How do you handle our content and data?",
    answer:
      "Crawls are limited to pages you authorize. Content is processed in-region (EU or US), encrypted at rest with AES-256, and deletable on request within 24 hours. We never train on customer content. SOC 2 Type II audit is in progress with completion expected this year.",
  },
  {
    question: "Can I export the data?",
    answer:
      "Every metric is available via REST API and CSV export on all plans. Agency adds scheduled BigQuery sync and white-label PDF reports. Webhooks fire on audit completion, drift alerts, and patch acceptance.",
  },
  {
    question: "How fast should we expect measurable lift?",
    answer:
      "Across our 41-domain beta cohort, the median was +11 percentage points of CPI within six weeks of applying patches, on queries that started below 0.5. Queries already above 0.8 move slower — there is simply less headroom.",
  },
];

export const DOC_SECTIONS: DocSection[] = [
  {
    group: "Getting started",
    links: [
      { label: "Introduction", href: "#introduction" },
      { label: "Quickstart", href: "#quickstart" },
      { label: "Authentication", href: "#authentication" },
    ],
  },
  {
    group: "Core concepts",
    links: [
      { label: "Citation Probability Interval", href: "#cpi" },
      { label: "Monte Carlo sampling", href: "#sampling" },
      { label: "NLI verification", href: "#nli" },
      { label: "Surgical patches", href: "#patches" },
    ],
  },
  {
    group: "API reference",
    links: [
      { label: "Audits", href: "#api-audits" },
      { label: "Projects", href: "#api-projects" },
      { label: "Webhooks", href: "#api-webhooks" },
    ],
  },
];
