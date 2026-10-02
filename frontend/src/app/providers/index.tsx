import type { ReactNode } from "react";
import { GSAPProvider } from "@/app/providers/GSAPProvider";
import { LenisProvider } from "@/app/providers/LenisProvider";
import { QueryProvider } from "@/app/providers/QueryProvider";
import { ThemeProvider } from "@/app/providers/ThemeProvider";

export { GSAPProvider } from "@/app/providers/GSAPProvider";
export { LenisProvider, useLenis } from "@/app/providers/LenisProvider";
export { QueryProvider } from "@/app/providers/QueryProvider";
export { ThemeProvider } from "@/app/providers/ThemeProvider";

/** Composition root for all app-wide providers. */
export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <QueryProvider>
      <ThemeProvider>
        <GSAPProvider>
          <LenisProvider>{children}</LenisProvider>
        </GSAPProvider>
      </ThemeProvider>
    </QueryProvider>
  );
}
