import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { Logo } from "@/components/shared/Logo";
import { ThemeToggle } from "@/components/shared/ThemeToggle";
import { Badge } from "@/components/ui/badge";

/**
 * Split auth shell: animated brand panel (desktop) + form column.
 * Mobile renders the form full-width.
 */
export function AuthLayout({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string;
  subtitle: string;
  children: ReactNode;
  footer: ReactNode;
}) {
  return (
    <div className="grid min-h-screen bg-background lg:grid-cols-2">
      {/* Brand panel */}
      <div className="relative hidden flex-col justify-between overflow-hidden border-r border-border bg-card p-12 lg:flex">
        <div aria-hidden="true" className="pointer-events-none absolute inset-0">
          <div className="absolute -left-24 top-[-160px] size-[480px] rounded-full bg-accent/25 blur-[130px] animate-gradient-pan" />
          <div className="absolute bottom-[-200px] right-[-120px] size-[520px] rounded-full bg-accent/15 blur-[140px] animate-gradient-pan-alt" />
          <div className="absolute inset-0 bg-noise opacity-[0.05] mix-blend-overlay" />
        </div>

        <div className="relative flex items-center justify-between">
          <Logo />
          <Badge variant="accent">Phase 1 demo</Badge>
        </div>

        <div className="relative">
          <p className="font-mono text-xs font-medium uppercase tracking-[0.18em] text-accent">
            Citation intelligence
          </p>
          <h2 className="mt-4 max-w-md font-heading text-h1 text-foreground">
            Measure the answer, not the anecdote.
          </h2>
          <p className="mt-4 max-w-sm text-body text-muted-foreground">
            Monte Carlo Citation Probability Intervals for ChatGPT Search, Google AI Overviews,
            and Perplexity — with the confidence bounds your reporting deserves.
          </p>
          <div className="mt-10 flex gap-8">
            {[
              { value: "N=10", label: "samples / query" },
              { value: "±5pp", label: "typical bounds" },
              { value: "0.94", label: "NLI precision" },
            ].map((stat) => (
              <div key={stat.label}>
                <p className="font-heading text-2xl font-semibold text-foreground">{stat.value}</p>
                <p className="mt-1 text-xs text-muted-foreground">{stat.label}</p>
              </div>
            ))}
          </div>
        </div>

        <p className="relative text-xs text-muted-foreground">
          “The first tool that told us a lift wasn’t significant.” — Devon Adewale, SEO Director
        </p>
      </div>

      {/* Form column */}
      <div className="relative flex min-h-screen flex-col items-center justify-center px-4 py-14 sm:px-8">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 opacity-40 [mask-image:radial-gradient(ellipse_70%_60%_at_50%_40%,black,transparent)]"
          style={{
            backgroundImage:
              "linear-gradient(hsl(var(--border) / 0.5) 1px, transparent 1px), linear-gradient(90deg, hsl(var(--border) / 0.5) 1px, transparent 1px)",
            backgroundSize: "48px 48px",
          }}
        />

        <div className="absolute left-4 top-4 sm:left-8 sm:top-6">
          <Link
            to="/"
            className="inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
          >
            <ArrowLeft className="size-4" />
            Back to site
          </Link>
        </div>
        <div className="absolute right-4 top-4 sm:right-8 sm:top-6">
          <ThemeToggle />
        </div>

        <div className="relative w-full max-w-md">
          <div className="mb-8 flex justify-center lg:hidden">
            <Logo />
          </div>

          <div className="glass rounded-2xl border border-border/70 p-8 shadow-card sm:p-10">
            <h1 className="font-heading text-h2 text-foreground">{title}</h1>
            <p className="mt-2 text-sm text-muted-foreground">{subtitle}</p>
            <div className="mt-8">{children}</div>
          </div>

          <div className="mt-6 text-center text-sm text-muted-foreground">{footer}</div>
        </div>
      </div>
    </div>
  );
}
