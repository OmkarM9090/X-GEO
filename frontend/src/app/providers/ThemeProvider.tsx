import { useEffect, type ReactNode } from "react";
import { useThemeStore } from "@/lib/store";

/** Keeps the persisted theme store, document class, and browser color scheme aligned. */
export function ThemeProvider({ children }: { children: ReactNode }) {
  const theme = useThemeStore((state) => state.theme);

  useEffect(() => {
    const root = document.documentElement;
    root.classList.toggle("dark", theme === "dark");
    root.style.colorScheme = theme;
  }, [theme]);

  return <>{children}</>;
}
