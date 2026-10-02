import { FileText } from "lucide-react";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { EmptyState } from "@/components/dashboard/EmptyState";

export default function ReportsPage() {
  return (
    <div>
      <PageHeader
        title="Reports"
        description="Weekly share-of-voice digests, drift summaries, and white-label exports."
        phaseTwo
      />
      <EmptyState
        Icon={FileText}
        title="Reports generate every Monday"
        description="CPI movement, drift alerts, and patch outcomes compiled into a board-ready PDF or a BigQuery rows export. Scheduling UI lands in Phase 2."
        phaseBadge
        className="min-h-[440px]"
      />
    </div>
  );
}
