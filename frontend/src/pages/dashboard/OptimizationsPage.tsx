import { Zap } from "lucide-react";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { EmptyState } from "@/components/dashboard/EmptyState";

export default function OptimizationsPage() {
  return (
    <div>
      <PageHeader
        title="Optimizations"
        description="Your prioritized patch queue — ranked by expected CPI lift per hour of editing."
        phaseTwo
      />
      <EmptyState
        Icon={Zap}
        title="Patch queue is warming up"
        description="Once the sampling backend ships, contradicted claims and retrieval misses will queue here as surgical patches — each with a measured lift estimate and a one-click diff export."
        phaseBadge
        className="min-h-[440px]"
      />
    </div>
  );
}
