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
