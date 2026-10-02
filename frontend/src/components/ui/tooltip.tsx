import { createContext, useContext, type HTMLAttributes, type ReactNode } from "react";
import { cn } from "@/lib/utils";

const TooltipContext = createContext(true);

export function TooltipProvider({ children }: { children: ReactNode }) {
  return <TooltipContext.Provider value>{children}</TooltipContext.Provider>;
}

export function Tooltip({ children, className }: { children: ReactNode; className?: string }) {
  return <span className={cn("group/tooltip relative inline-flex", className)}>{children}</span>;
}

export function TooltipTrigger({ children, className, ...props }: HTMLAttributes<HTMLElement>) {
  const available = useContext(TooltipContext);
  if (!available) return <>{children}</>;
  return <span tabIndex={0} className={cn("outline-none", className)} {...props}>{children}</span>;
}

export function TooltipContent({ children, className, side = "top" }: { children: ReactNode; className?: string; side?: "top" | "bottom" | "left" | "right" }) {
  const position = {
    top: "bottom-full left-1/2 mb-2 -translate-x-1/2",
    bottom: "left-1/2 top-full mt-2 -translate-x-1/2",
    left: "right-full top-1/2 mr-2 -translate-y-1/2",
    right: "left-full top-1/2 ml-2 -translate-y-1/2",
  }[side];

  return (
    <span
      role="tooltip"
      className={cn(
        "pointer-events-none absolute z-50 max-w-64 whitespace-nowrap rounded-md border border-border bg-card px-2.5 py-1.5 text-xs text-card-foreground opacity-0 shadow-card transition-opacity group-hover/tooltip:opacity-100 group-focus-within/tooltip:opacity-100",
        position,
        className,
      )}
    >
      {children}
    </span>
  );
}
