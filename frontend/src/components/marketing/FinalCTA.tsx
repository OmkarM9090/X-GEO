import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { useSplitText } from "@/hooks/useSplitText";
import { useReveal } from "@/hooks/useScrollTrigger";
import { MagneticButton } from "@/components/shared/MagneticButton";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

/** Final CTA — gradient card with slow panning radial glows + grain. */
export function FinalCTA() {
  const headlineRef = useSplitText<HTMLHeadingElement>({ kind: "lines" });
  const cardRef = useReveal<HTMLDivElement>({ selector: "[data-cta]", y: 32, start: "top 85%" });
  const [email, setEmail] = useState("");
  const navigate = useNavigate();

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    navigate(email ? `/signup?email=${encodeURIComponent(email)}` : "/signup");
  };

  return (
    <section className="px-4 py-24 sm:px-6 md:py-32 lg:px-8" ref={cardRef}>
      <div
        data-cta
        className="relative mx-auto w-full max-w-7xl overflow-hidden rounded-3xl border border-border bg-card px-6 py-20 text-center shadow-card md:py-28"
      >
        <div aria-hidden="true" className="pointer-events-none absolute inset-0">
          <div className="absolute -left-32 -top-32 size-[420px] rounded-full bg-accent/25 blur-[120px] animate-gradient-pan" />
          <div className="absolute -bottom-40 -right-24 size-[460px] rounded-full bg-accent/15 blur-[130px] animate-gradient-pan-alt" />
          <div className="absolute inset-0 bg-noise opacity-[0.04] mix-blend-overlay" />
        </div>

        <div className="relative">
          <p className="font-mono text-xs font-medium uppercase tracking-[0.18em] text-accent">
            Start measuring
          </p>
          <h2
            ref={headlineRef}
            className="mx-auto mt-4 max-w-2xl font-heading text-display text-foreground"
          >
            Ready to measure what matters?
          </h2>
          <p className="mx-auto mt-5 max-w-xl text-body-lg text-muted-foreground">
            Drop in a work email. Ten Monte Carlo audits on your own content, free — first
            interval in under an hour.
          </p>

          <form
            onSubmit={onSubmit}
            className="mx-auto mt-10 flex max-w-md flex-col gap-3 sm:flex-row"
          >
            <Input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@company.com"
              aria-label="Work email"
              className="flex-1 bg-background/70 backdrop-blur"
            />
            <MagneticButton strength={0.2}>
              <Button type="submit" variant="accent" className="w-full sm:w-auto">
                Start Free Audit
                <ArrowRight className="size-4" />
              </Button>
            </MagneticButton>
          </form>

          <p className="mt-6 text-xs text-muted-foreground">
            Free tier · 10 audits · No credit card · Cancel anytime
          </p>
        </div>
      </div>
    </section>
  );
}
