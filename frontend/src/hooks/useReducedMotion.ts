import { useMediaQuery } from "@/hooks/useMediaQuery";

/** True when the operating system requests less motion. */
export function useReducedMotion(): boolean {
  return useMediaQuery("(prefers-reduced-motion: reduce)");
}
