import type { LucideIcon } from "lucide-react";

/* ---------- Domain ---------- */

export type Engine = "chatgpt" | "aio" | "perplexity";

export type AuditStatus = "completed" | "running" | "failed" | "scheduled";

export interface CitationSample {
  run: number;
  probability: number;
  temperature: number;
  cited: boolean;
}

export interface Audit {
  id: string;
  query: string;
  engine: Engine;
  cpi: number;
  lower: number;
  upper: number;
  delta: number;
  status: AuditStatus;
  runs: number;
  updatedAt: string;
}

export interface TrendPoint {
  date: string;
  chatgpt: number;
  aio: number;
  perplexity: number;
}

export interface MetricDelta {
  value: number;
  delta: number;
}

export interface DashboardMetrics {
  avgCpi: MetricDelta;
  nliPrecision: MetricDelta;
  activeAudits: MetricDelta;
  monthlyRuns: MetricDelta & { limit: number };
}

export interface AppNotification {
  id: string;
  title: string;
  description: string;
  time: string;
  unread: boolean;
  kind: "audit" | "alert" | "report";
}

/* ---------- Marketing ---------- */

export interface LogoItem {
  name: string;
  Icon: LucideIcon;
}

export interface BentoFeature {
  title: string;
  description: string;
  span: "wide" | "tile";
  key: string;
}

export interface HowItWorksStep {
  index: string;
  title: string;
  description: string;
  detail: string;
  Icon: LucideIcon;
}

export interface PricingTier {
  name: string;
  price: number | null;
  period: string;
  description: string;
  features: string[];
  cta: string;
  featured: boolean;
}

export interface Testimonial {
  quote: string;
  name: string;
  role: string;
  company: string;
  initials: string;
}

export interface FAQItem {
  question: string;
  answer: string;
}

export interface DocSection {
  group: string;
  links: { label: string; href: string }[];
}

export interface CommandItem {
  id: string;
  label: string;
  hint: string;
  group: "Navigate" | "Actions" | "Audits";
}
