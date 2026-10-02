import { Folder, Plus } from "lucide-react";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { Button } from "@/components/ui/button";

export default function ProjectsPage() {
  return (
    <div>
      <PageHeader title="Projects" description="Group audits by domain, client, or product line." phaseTwo>
        <Button variant="accent" size="sm" disabled>
          <Plus className="size-4" />
          New project
        </Button>
      </PageHeader>
      <EmptyState
        Icon={Folder}
        title="Project grouping arrives with the backend"
        description="Projects will let you segment CPI by domain and locale, assign crawls, and roll up share-of-voice per client. Mock grouping ships in Phase 2."
        phaseBadge
        className="min-h-[440px]"
      />
    </div>
  );
}
