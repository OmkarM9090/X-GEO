export type ProjectStatus = "active" | "paused";

export interface Project {
  id: string;
  name: string;
  domain: string;
  description: string;
  engineCount: number;
  trackedQueries: number;
  avgCpi: number;
  change: number;
  updatedAt: string;
  status: ProjectStatus;
}
