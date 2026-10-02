import { SkeletonShimmer } from "@/components/animations/SkeletonShimmer";
import { cn } from "@/lib/utils";

interface SkeletonCardProps {
  loading: boolean;
  children?: React.ReactNode;
  className?: string;
  index?: number;
  rows?: number;
}

/** Dashboard-sized skeleton surface, using the same radius and shimmer as the marketing mockup. */
export function SkeletonCard({ loading, children, className, index, rows = 3 }: SkeletonCardProps) {
  return (
    <SkeletonShimmer
      loading={loading}
      index={index}
      className={cn("min-h-[190px]", className)}
      skeletonClassName="border-0 bg-card"
      skeleton={
        <div className="space-y-5 p-5" aria-hidden="true">
          <div className="h-3 w-1/3 rounded-full bg-foreground/[0.07]" />
          <div className="h-7 w-1/2 rounded-md bg-foreground/[0.07]" />
          <div className="space-y-2.5 pt-2">
            {Array.from({ length: rows }, (_, row) => (
              <div key={row} className={cn("h-2.5 rounded-full bg-foreground/[0.055]", row === rows - 1 ? "w-2/3" : "w-full")} />
            ))}
          </div>
        </div>
      }
    >
      {children}
    </SkeletonShimmer>
  );
}
