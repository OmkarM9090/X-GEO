import type { PricingTier } from "@/types";

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
