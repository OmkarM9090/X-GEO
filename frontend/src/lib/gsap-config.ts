import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { SplitText } from "gsap/SplitText";
import { Flip } from "gsap/Flip";
import { useGSAP } from "@gsap/react";

let pluginsRegistered = false;

/** Register the app's GSAP plugins exactly once, even under React StrictMode. */
export function registerGSAPPlugins(): void {
  if (pluginsRegistered) return;
  gsap.registerPlugin(ScrollTrigger, SplitText, Flip, useGSAP);
  gsap.defaults({ ease: "power3.out", duration: 0.7 });
  pluginsRegistered = true;
}

// Module-level registration makes imported animation hooks safe before providers mount.
registerGSAPPlugins();

export const MOTION_OK = "(prefers-reduced-motion: no-preference)";

export { gsap, ScrollTrigger, SplitText, Flip, useGSAP };
