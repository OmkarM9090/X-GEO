import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

/** Native, accessible overflow region that works with Lenis' nested-scroll guard. */
export function ScrollArea({ className, children, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      data-lenis-prevent
      className={cn("overflow-auto overscroll-contain [scrollbar-color:hsl(var(--muted-foreground)/.28)_transparent] [scrollbar-width:thin]", className)}
      {...props}
    >
      {children}
    </div>
  );
}
