import { useEffect, type ReactNode } from "react";
import { registerGSAPPlugins, ScrollTrigger } from "@/lib/gsap-config";

/** Central app-level owner for GSAP plugins and resize refresh coordination. */
export function GSAPProvider({ children }: { children: ReactNode }) {
  useEffect(() => {
    registerGSAPPlugins();
    ScrollTrigger.refresh();

    let resizeTimer = 0;
    const refreshAfterResize = () => {
      window.clearTimeout(resizeTimer);
      resizeTimer = window.setTimeout(() => ScrollTrigger.refresh(), 180);
    };
    window.addEventListener("resize", refreshAfterResize, { passive: true });

    return () => {
      window.clearTimeout(resizeTimer);
      window.removeEventListener("resize", refreshAfterResize);
    };
  }, []);

  return <>{children}</>;
}
