import { Link } from "react-router-dom";
import { ArrowLeft, BarChart3, GitPullRequest, ScanSearch, ShieldCheck } from "lucide-react";
import { ENGINE_LABELS, RECENT_AUDITS } from "@/data/mock-audits";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

/** Shell for the audit detail view — header carries real mock data. */
export default function AuditDetailPage() {
  const audit = RECENT_AUDITS[0];

  return (
    <div>
      <Button variant="ghost" size="sm" asChild className="-ml-2 mb-4 text-muted-foreground">
        <Link to="/dashboard">
          <ArrowLeft className="size-4" />
          Back to overview
        </Link>
      </Button>

      <div className="mb-8 flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="font-mono text-xs text-muted-foreground">{audit.id} · {ENGINE_LABELS[audit.engine]} · n={audit.runs}</p>
          <h1 className="mt-1.5 max-w-2xl font-heading text-h1 text-foreground">“{audit.query}”</h1>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <Badge variant="success">Completed</Badge>
            <Badge variant="accent">CPI {audit.cpi.toFixed(2)}</Badge>
            <Badge variant="outline" className="font-mono">
              95% CI [{audit.lower.toFixed(2)}, {audit.upper.toFixed(2)}]
            </Badge>
            <Badge variant="outline" className="font-mono text-success">+6.0pp / 7d</Badge>
          </div>
        </div>
        <Button variant="outline" size="sm" disabled>
          <ScanSearch className="size-4" />
          Re-run audit
        </Button>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <EmptyState
          Icon={BarChart3}
          title="Sample distribution"
          description="Per-run citation outcomes across the temperature sweep, with Wilson bounds."
          phaseBadge
        />
        <EmptyState
          Icon={ShieldCheck}
          title="NLI claim audit"
          description="Entailed, contradicted, and unsupported claims linked to source chunks."
          phaseBadge
        />
        <EmptyState
          Icon={GitPullRequest}
          title="Suggested patches"
          description="Chunk-level diffs ranked by expected CPI lift, with confirmation audits."
          phaseBadge
        />
      </div>
    </div>
  );
}
