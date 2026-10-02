import { useRef, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Check } from "lucide-react";
import { gsap, useGSAP, MOTION_OK } from "@/lib/gsap-config";
import { useSplitText } from "@/hooks/useSplitText";
import { useReveal } from "@/hooks/useScrollTrigger";
import { MagneticButton } from "@/components/shared/MagneticButton";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { PRICING_TIERS } from "@/data/pricing";
import type { PricingTier } from "@/types";
import { cn } from "@/lib/utils";

/**
 * 3D tilt wrapper — rotationX/Y driven by cursor position inside a
 * perspective container; elastic settle on leave. Pointer-fine only.
 */
function TiltCard({ children, featured }: { children: ReactNode; featured?: boolean }) {
  const ref = useRef<HTMLDivElement>(null);

  useGSAP(
    () => {
      const el = ref.current;
      if (!el) return undefined;
      const mm = gsap.matchMedia();
      mm.add(`${MOTION_OK} and (hover: hover) and (pointer: fine)`, () => {
        const rxTo = gsap.quickTo(el, "rotationX", { duration: 0.5, ease: "power3.out" });
        const ryTo = gsap.quickTo(el, "rotationY", { duration: 0.5, ease: "power3.out" });

        const onMove = (event: MouseEvent) => {
          const rect = el.getBoundingClientRect();
          const px = (event.clientX - rect.left) / rect.width - 0.5;
          const py = (event.clientY - rect.top) / rect.height - 0.5;
          ryTo(px * 7);
          rxTo(py * -7);
        };
        const onLeave = () => {
          gsap.to(el, { rotationX: 0, rotationY: 0, duration: 0.9, ease: "elastic.out(1, 0.45)" });
        };

        el.addEventListener("mousemove", onMove);
        el.addEventListener("mouseleave", onLeave);
        return () => {
          el.removeEventListener("mousemove", onMove);
          el.removeEventListener("mouseleave", onLeave);
        };
      });
      return () => mm.revert();
    },
    { scope: ref },
  );

  return (
    <div style={{ perspective: "1200px" }} data-reveal>
      <div
        ref={ref}
        className={cn(
          "flex h-full flex-col rounded-2xl border bg-card p-8 will-change-transform [transform-style:preserve-3d]",
          featured
            ? "relative border-accent/60 shadow-glow"
            : "border-border transition-colors duration-300 hover:border-muted-foreground/30",
        )}
      >
        {children}
      </div>
    </div>
  );
}

function TierCard({ tier }: { tier: PricingTier }) {
  return (
    <TiltCard featured={tier.featured}>
      {tier.featured && (
        <Badge variant="accent" className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1">
          Most popular
        </Badge>
      )}
      <div className="flex items-baseline justify-between">
        <h3 className="font-heading text-h3 text-foreground">{tier.name}</h3>
        {tier.price !== null && (
          <span className="font-mono text-xs text-muted-foreground">{tier.period}</span>
        )}
      </div>
      <div className="mt-4 flex items-baseline gap-1">
        <span className="font-heading text-[44px] font-semibold leading-none tracking-[-0.03em] text-foreground">
          {tier.price === null ? "Custom" : `$${tier.price}`}
        </span>
        {tier.price !== null && tier.price > 0 && <span className="text-sm text-muted-foreground">/mo</span>}
      </div>
      <p className="mt-3 text-sm text-muted-foreground">{tier.description}</p>

      <ul className="mt-7 flex-1 space-y-2.5 border-t border-border pt-6">
        {tier.features.map((feature) => (
          <li key={feature} className="flex items-start gap-2.5 text-sm text-foreground/85">
            <Check className="mt-0.5 size-4 shrink-0 text-accent" strokeWidth={2.5} />
            {feature}
          </li>
        ))}
      </ul>

      <MagneticButton strength={0.2} className="mt-8 block">
        <Button
          variant={tier.featured ? "accent" : "outline"}
          className="w-full"
          asChild
        >
          <Link to="/signup">{tier.cta}</Link>
        </Button>
      </MagneticButton>
    </TiltCard>
  );
}

export function PricingTiers() {
  const headlineRef = useSplitText<HTMLHeadingElement>({ kind: "lines" });
  const gridRef = useReveal<HTMLDivElement>({ stagger: 0.12, start: "top 80%" });

  return (
    <section id="pricing" className="py-24 md:py-32">
      <div className="mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <p className="font-mono text-xs font-medium uppercase tracking-[0.18em] text-accent">
            Pricing
          </p>
          <h2 ref={headlineRef} className="mt-4 font-heading text-display text-foreground">
            Pay for samples, not seats.
          </h2>
          <p className="mt-5 text-body-lg text-muted-foreground">
            Every plan includes all three engines and the full CPI math. Upgrade when your
            query volume grows.
          </p>
        </div>

        <div ref={gridRef} className="mt-16 grid gap-5 md:grid-cols-3">
          {PRICING_TIERS.map((tier) => (
            <TierCard key={tier.name} tier={tier} />
          ))}
        </div>

        <div
          data-reveal
          className="mt-5 flex flex-col items-start justify-between gap-5 rounded-2xl border border-dashed border-border bg-card/50 p-6 sm:flex-row sm:items-center md:p-8"
        >
          <div>
            <p className="font-heading text-h3 text-foreground">
              Enterprise <span className="ml-2 font-mono text-sm font-normal text-muted-foreground">$2,000+/mo</span>
            </p>
            <p className="mt-2 max-w-xl text-sm text-muted-foreground">
              Dedicated sampling clusters, SSO/SAML, custom DPA, and a 99.9% sampling SLA for
              organizations measuring thousands of queries.
            </p>
          </div>
          <Button variant="outline" asChild className="shrink-0">
            <a href="mailto:sales@xgeo.dev">
              Contact sales
              <ArrowRight className="size-4" />
            </a>
          </Button>
        </div>
      </div>
    </section>
  );
}
