export const NAV_LINKS = [
  { label: "Features", to: "/features" },
  { label: "How it Works", to: "/#how-it-works", hash: true },
  { label: "Pricing", to: "/pricing" },
  { label: "Docs", to: "/docs" },
] as const;

export const MARKETING_ANCHORS = {
  demo: "#demo",
  features: "#features",
  howItWorks: "#how-it-works",
  pricing: "#pricing",
  testimonials: "#testimonials",
  faq: "#faq",
} as const;

export const ROUTES = {
  home: "/",
  features: "/features",
  pricing: "/pricing",
  docs: "/docs",
  changelog: "/changelog",
  signIn: "/signin",
  signUp: "/signup",
  dashboard: "/dashboard",
} as const;
