import type { AppNotification, Audit, CommandItem, Engine } from "@/types";

export const ENGINE_LABELS: Record<Engine, string> = {
  chatgpt: "ChatGPT Search",
  aio: "Google AIO",
  perplexity: "Perplexity",
};

/* ---------- Stochastic demo (USP) ---------- */
export const RECENT_AUDITS: Audit[] = [
  { id: "A-1042", query: "best headless CMS for e-commerce teams", engine: "chatgpt", cpi: 0.71, lower: 0.65, upper: 0.77, delta: 0.06, status: "completed", runs: 10, updatedAt: "12 min ago" },
  { id: "A-1041", query: "acme vs nortide uptime SLA comparison", engine: "perplexity", cpi: 0.54, lower: 0.47, upper: 0.61, delta: -0.03, status: "completed", runs: 10, updatedAt: "44 min ago" },
  { id: "A-1040", query: "how to rotate API keys on Acme", engine: "aio", cpi: 0.83, lower: 0.78, upper: 0.88, delta: 0.11, status: "completed", runs: 10, updatedAt: "1 h ago" },
  { id: "A-1039", query: "SOC 2 compliant vector database vendors", engine: "chatgpt", cpi: 0.47, lower: 0.40, upper: 0.54, delta: 0.02, status: "running", runs: 7, updatedAt: "running" },
  { id: "A-1038", query: "enterprise pricing for Acme platform", engine: "perplexity", cpi: 0.66, lower: 0.60, upper: 0.72, delta: 0.04, status: "scheduled", runs: 0, updatedAt: "queued 18:00" },
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
