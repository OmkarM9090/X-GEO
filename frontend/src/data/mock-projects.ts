import type { Project } from "@/types";

/** Typed fixtures used by the Phase 1 projects dashboard. */
export const MOCK_PROJECTS: Project[] = [
  {
    id: "prj_acme_docs",
    name: "Acme Docs",
    domain: "docs.acme.dev",
    description: "Developer documentation and API references",
    engineCount: 3,
    trackedQueries: 42,
    avgCpi: 0.62,
    change: 0.041,
    updatedAt: "12 minutes ago",
    status: "active",
  },
  {
    id: "prj_acme_blog",
    name: "Acme Journal",
    domain: "acme.dev/blog",
    description: "Product education and editorial content",
    engineCount: 3,
    trackedQueries: 18,
    avgCpi: 0.48,
    change: -0.012,
    updatedAt: "1 hour ago",
    status: "active",
  },
  {
    id: "prj_nortide",
    name: "Nortide Workspace",
    domain: "nortide.io",
    description: "Shared workspace · last audited yesterday",
    engineCount: 2,
    trackedQueries: 26,
    avgCpi: 0.71,
    change: 0.063,
    updatedAt: "Yesterday",
    status: "active",
  },
];
