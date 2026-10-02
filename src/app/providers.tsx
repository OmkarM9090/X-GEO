import { useEffect, type ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { LenisProvider } from "@/hooks/useLenis";
import { useThemeStore } from "@/lib/store";

/** TanStack Query client — ready for the Phase 2 API layer. */
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

export function QueryProvider({ children }: { children: ReactNode }) {
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}

/**
 * Syncs the persisted theme preference to <html class="dark"> on mount
 * and whenever the store changes. Default: dark.
 */
export function ThemeProvider({ children }: { children: ReactNode }) {
  const theme = useThemeStore((s) => s.theme);
  useEffect(() => {
    const root = document.documentElement;
    root.classList.toggle("dark", theme === "dark");
    root.style.colorScheme = theme;
  }, [theme]);
  return <>{children}</>;
}

export { LenisProvider };

/** Composition root for all app-wide providers. */
export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <QueryProvider>
      <ThemeProvider>
        <LenisProvider>{children}</LenisProvider>
      </ThemeProvider>
    </QueryProvider>
  );
}
