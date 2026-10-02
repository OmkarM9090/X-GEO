import { Moon, Sun } from "lucide-react";
import { useThemeStore } from "@/lib/store";
import { cn } from "@/lib/utils";

/**
 * Sun/moon toggle. Icons cross-fade with a 180° rotation over 400ms
 * (cubic-bezier theme morph); background color shifts via CSS variables.
 */
export function ThemeToggle({ className }: { className?: string }) {
  const toggleTheme = useThemeStore((s) => s.toggleTheme);
  const theme = useThemeStore((s) => s.theme);

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
      aria-pressed={theme === "dark"}
      className={cn(
        "relative grid size-9 place-items-center overflow-hidden rounded-lg border border-border/60",
        "text-muted-foreground transition-colors duration-300 hover:border-border hover:bg-muted/50 hover:text-foreground",
        className,
      )}
    >
      <Sun
        className="size-[17px] rotate-0 scale-100 transition-all duration-[400ms] ease-theme-morph dark:-rotate-180 dark:scale-0"
        aria-hidden="true"
      />
      <Moon
        className="absolute size-[17px] rotate-180 scale-0 transition-all duration-[400ms] ease-theme-morph dark:rotate-0 dark:scale-100"
        aria-hidden="true"
      />
    </button>
  );
}
