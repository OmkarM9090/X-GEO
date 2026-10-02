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
