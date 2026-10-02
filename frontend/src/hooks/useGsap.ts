import { gsap, useGSAP, MOTION_OK } from "@/lib/gsap-config";

type GSAPCallback = Parameters<typeof useGSAP>[0];
type GSAPConfig = Parameters<typeof useGSAP>[1];

/**
 * App-wide wrapper around @gsap/react's useGSAP.
 * All animations should flow through this hook; wrap tween creation in a
 * `gsap.matchMedia().add(MOTION_OK, ...)` block so reduced-motion users
 * always see the fully-rendered final state.
 */
export function useGsap(callback: GSAPCallback, config?: GSAPConfig): void {
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useGSAP(callback, config);
}

export { gsap, MOTION_OK };
