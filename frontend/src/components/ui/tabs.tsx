import { createContext, useContext, useId, useState, type KeyboardEvent, type ReactNode } from "react";
import { cn } from "@/lib/utils";

interface TabsContextValue {
  value: string;
  setValue: (value: string) => void;
  id: string;
}

const TabsContext = createContext<TabsContextValue | null>(null);

function useTabsContext() {
  const context = useContext(TabsContext);
  if (!context) throw new Error("Tabs components must be rendered inside <Tabs>");
  return context;
}

export function Tabs({
  value,
  defaultValue = "",
  onValueChange,
  children,
  className,
}: {
  value?: string;
  defaultValue?: string;
  onValueChange?: (value: string) => void;
  children: ReactNode;
  className?: string;
}) {
  const [uncontrolledValue, setUncontrolledValue] = useState(defaultValue);
  const id = useId();
  const activeValue = value ?? uncontrolledValue;
  const setValue = (nextValue: string) => {
    if (value === undefined) setUncontrolledValue(nextValue);
    onValueChange?.(nextValue);
  };

  return (
    <TabsContext.Provider value={{ value: activeValue, setValue, id }}>
      <div className={cn("w-full", className)}>{children}</div>
    </TabsContext.Provider>
  );
}

export function TabsList({ className, children, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  const context = useTabsContext();
  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    const keys = ["ArrowLeft", "ArrowRight", "Home", "End"];
    if (!keys.includes(event.key)) return;
    event.preventDefault();
    const triggers = Array.from(event.currentTarget.querySelectorAll<HTMLButtonElement>("[role='tab']:not(:disabled)"));
    const index = triggers.indexOf(document.activeElement as HTMLButtonElement);
    const nextIndex = event.key === "Home" ? 0 : event.key === "End" ? triggers.length - 1 : (index + (event.key === "ArrowRight" ? 1 : -1) + triggers.length) % triggers.length;
    const next = triggers[nextIndex];
    next?.focus();
    if (next?.dataset.value) context.setValue(next.dataset.value);
  };

  return <div role="tablist" onKeyDown={onKeyDown} className={cn("inline-flex items-center gap-1 rounded-lg border border-border bg-muted/50 p-1", className)} {...props}>{children}</div>;
}

export function TabsTrigger({ value, className, children, ...props }: React.ButtonHTMLAttributes<HTMLButtonElement> & { value: string }) {
  const context = useTabsContext();
  const selected = context.value === value;
  const tabId = `${context.id}-tab-${value}`;
  const panelId = `${context.id}-panel-${value}`;

  return (
    <button
      type="button"
      role="tab"
      id={tabId}
      data-value={value}
      aria-selected={selected}
      aria-controls={panelId}
      tabIndex={selected ? 0 : -1}
      onClick={() => context.setValue(value)}
      className={cn("inline-flex min-h-8 items-center justify-center rounded-md px-3 text-xs font-medium text-muted-foreground outline-none transition-colors hover:text-foreground focus-visible:ring-2 focus-visible:ring-accent/50", selected && "bg-card text-foreground shadow-sm", className)}
      {...props}
    >
      {children}
    </button>
  );
}

export function TabsContent({ value, className, children, ...props }: React.HTMLAttributes<HTMLDivElement> & { value: string }) {
  const context = useTabsContext();
  if (context.value !== value) return null;

  return (
    <div
      role="tabpanel"
      id={`${context.id}-panel-${value}`}
      aria-labelledby={`${context.id}-tab-${value}`}
      tabIndex={0}
      className={cn("mt-3 outline-none focus-visible:ring-2 focus-visible:ring-accent/50", className)}
      {...props}
    >
      {children}
    </div>
  );
}
