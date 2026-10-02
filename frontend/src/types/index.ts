import type { LucideIcon } from "lucide-react";

export * from "@/types/audit";
export * from "@/types/project";
export * from "@/types/metrics";
export * from "@/types/user";

export interface LogoItem {
  name: string;
  Icon: LucideIcon;
  asset?: string;
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
