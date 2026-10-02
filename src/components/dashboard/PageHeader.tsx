import type { ReactNode } from "react";
import { Badge } from "@/components/ui/badge";

/** Consistent dashboard page header: title, description, actions, phase tag. */
export function PageHeader({
  title,
  description,
  phaseTwo = false,
  children,
}: {
  title: string;
  description: string;
  phaseTwo?: boolean;
  children?: ReactNode;
}) {
  return (
    <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
      <div>
        <div className="flex items-center gap-3">
          <h1 className="font-heading text-h1 text-foreground">{title}</h1>
          {phaseTwo && <Badge variant="accent">Phase 2</Badge>}
        </div>
        <p className="mt-1.5 text-sm text-muted-foreground">{description}</p>
      </div>
      {children && <div className="flex items-center gap-2">{children}</div>}
    </div>
  );
}
