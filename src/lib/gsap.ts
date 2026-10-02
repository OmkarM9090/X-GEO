import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { SplitText } from "gsap/SplitText";
import { Flip } from "gsap/Flip";
import { useGSAP } from "@gsap/react";

/**
 * Central GSAP registration — import from "@/lib/gsap" everywhere
 * so plugins are registered exactly once.
 */
gsap.registerPlugin(ScrollTrigger, SplitText, Flip, useGSAP);

gsap.defaults({ ease: "power3.out", duration: 0.7 });

export const MOTION_OK = "(prefers-reduced-motion: no-preference)";

export { gsap, ScrollTrigger, SplitText, Flip, useGSAP };
