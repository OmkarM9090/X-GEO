import { useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { gsap, useGSAP, ScrollTrigger, MOTION_OK } from "@/lib/gsap-config";
import { useReducedMotion } from "@/hooks/useReducedMotion";

interface PageTransitionProps {
  children: ReactNode;
  routeKey: string;
}

/** Exit/enter route wrapper implemented with GSAP while preserving the outgoing outlet for 200ms. */
export function PageTransition({ children, routeKey }: PageTransitionProps) {
  const rootRef = useRef<HTMLDivElement>(null);
  const latestChildren = useRef(children);
  const activeKey = useRef(routeKey);
  const [visibleChildren, setVisibleChildren] = useState(children);
  const reducedMotion = useReducedMotion();

  useLayoutEffect(() => {
    latestChildren.current = children;
  }, [children]);

  useGSAP(
    () => {
      const root = rootRef.current;
      if (!root || activeKey.current === routeKey) return undefined;

      activeKey.current = routeKey;
      ScrollTrigger.getAll().forEach((trigger) => {
        if (trigger.vars.id !== "xgeo-scroll-progress") trigger.kill();
      });

      if (reducedMotion) {
        setVisibleChildren(latestChildren.current);
        return undefined;
      }

      const media = gsap.matchMedia();
      media.add(MOTION_OK, () => {
        gsap.set(root, { willChange: "transform, opacity" });
        const timeline = gsap.timeline({
          onComplete: () => {
            gsap.set(root, { clearProps: "willChange" });
            ScrollTrigger.refresh();
          },
        });

        timeline.to(root, {
          opacity: 0,
          y: -6,
          duration: 0.2,
          ease: "power2.in",
          onComplete: () => {
            setVisibleChildren(latestChildren.current);
            requestAnimationFrame(() => {
              if (!root.isConnected) return;
              gsap.fromTo(
                root,
                { opacity: 0, y: 20 },
                {
                  opacity: 1,
                  y: 0,
                  duration: 0.4,
                  ease: "power3.out",
                  clearProps: "willChange",
                  onComplete: () => ScrollTrigger.refresh(),
                },
              );
            });
          },
        });

        return () => timeline.kill();
      });

      return () => media.revert();
    },
    { scope: rootRef, dependencies: [routeKey, reducedMotion], revertOnUpdate: true },
  );

  return (
    <div ref={rootRef} className="page-transition-layer">
      {visibleChildren}
    </div>
  );
}
