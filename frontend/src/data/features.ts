import { Aperture, Box, Circle, Compass, Dices, Database, Globe, Hexagon, Layers, ShieldCheck, Square, Triangle } from "lucide-react";
import type { BentoFeature, HowItWorksStep, LogoItem } from "@/types";

export const LOGOS: LogoItem[] = [
  { name: "Nortide", Icon: Hexagon, asset: "/images/logos/nortide.svg" },
  { name: "Vektor Labs", Icon: Triangle, asset: "/images/logos/vektor-labs.svg" },
  { name: "Loomfield", Icon: Square, asset: "/images/logos/loomfield.svg" },
  { name: "Parsec", Icon: Circle, asset: "/images/logos/parsec.svg" },
  { name: "Helios Data", Icon: Aperture, asset: "/images/logos/helios-data.svg" },
  { name: "Cairn Systems", Icon: Layers, asset: "/images/logos/cairn-systems.svg" },
  { name: "Quanta", Icon: Box, asset: "/images/logos/quanta.svg" },
  { name: "Fjordline", Icon: Compass, asset: "/images/logos/fjordline.svg" },
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
