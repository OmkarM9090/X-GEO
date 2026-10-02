import { ArrowRight, ArrowUpRight, Building2, Check, Plus } from "lucide-react";
import { Link } from "react-router-dom";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { useReveal } from "@/hooks/useScrollTrigger";
import { MOCK_PROJECTS } from "@/data/mock-projects";
import { cn } from "@/lib/utils";

export default function ProjectsPage() {
  const projectsRef = useReveal<HTMLDivElement>({ stagger: 0.09, start: "top 92%", y: 16 });

  return (
    <div>
      <PageHeader title="Projects" description="Group audits by domain, client, or product line.">
        <Button variant="accent" size="sm" disabled title="Project creation is enabled with the Phase 2 API">
          <Plus className="size-4" />
          New project
        </Button>
      </PageHeader>

      <div ref={projectsRef} className="grid gap-4 lg:grid-cols-2">
        {MOCK_PROJECTS.map((project) => (
          <Card
            key={project.id}
            data-reveal
            data-cursor="interactive"
            className="group overflow-hidden transition-colors hover:border-accent/40"
          >
            <div className="flex items-start justify-between gap-4 p-5 sm:p-6">
              <div className="flex min-w-0 items-center gap-3.5">
                <span className="grid size-11 shrink-0 place-items-center rounded-xl border border-accent/20 bg-accent/10 text-accent">
                  <Building2 className="size-5" />
                </span>
                <div className="min-w-0">
                  <h2 className="truncate font-heading text-[16px] font-semibold text-foreground">{project.name}</h2>
                  <p className="mt-1 truncate font-mono text-xs text-muted-foreground">{project.domain}</p>
                </div>
              </div>
            </div>

            <div className="px-5 pb-5 sm:px-6 sm:pb-6">
              <p className="text-sm text-muted-foreground">{project.description}</p>
              <div className="mt-5 grid grid-cols-3 divide-x divide-border rounded-xl border border-border/70 bg-background/40 py-3">
                <div className="px-3 text-center">
                  <p className="font-mono text-lg font-medium text-foreground">{project.trackedQueries}</p>
                  <p className="mt-1 text-[10px] text-muted-foreground">Tracked queries</p>
                </div>
                <div className="px-3 text-center">
                  <p className="font-mono text-lg font-medium text-foreground">{project.engineCount}</p>
                  <p className="mt-1 text-[10px] text-muted-foreground">AI engines</p>
                </div>
                <div className="px-3 text-center">
                  <p className="font-mono text-lg font-medium text-foreground">{Math.round(project.avgCpi * 100)}%</p>
                  <p className="mt-1 text-[10px] text-muted-foreground">Average CPI</p>
                </div>
              </div>

              <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <Badge variant="success"><Check className="size-3" /> Active</Badge>
                  <span className={cn("inline-flex items-center gap-1 font-mono text-[11px]", project.change >= 0 ? "text-success" : "text-danger")}>
                    <ArrowUpRight className={cn("size-3", project.change < 0 && "rotate-90")} />
                    {project.change >= 0 ? "+" : "−"}{Math.abs(project.change * 100).toFixed(1)}pp
                  </span>
                </div>
                <p className="text-[11px] text-muted-foreground">Updated {project.updatedAt}</p>
              </div>
              <div className="mt-5 flex justify-end border-t border-border/70 pt-4">
                <Link to="/dashboard/audits" className="inline-flex items-center gap-1.5 text-xs font-medium text-muted-foreground transition-colors hover:text-accent">
                  View audits <ArrowRight className="size-3.5" />
                </Link>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
