import type { CitationSample, DashboardMetrics, TrendPoint } from "@/types";

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
