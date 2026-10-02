import type { DocSection, FAQItem } from "@/types";

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
