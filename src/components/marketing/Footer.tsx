import { Link } from "react-router-dom";
import { AtSign, GitBranch, Rss } from "lucide-react";
import { Logo } from "@/components/shared/Logo";
import { ThemeToggle } from "@/components/shared/ThemeToggle";

const COLUMNS: { title: string; links: { label: string; to: string }[] }[] = [
  {
    title: "Product",
    links: [
      { label: "Features", to: "/features" },
      { label: "Pricing", to: "/pricing" },
      { label: "Changelog", to: "/docs#changelog" },
      { label: "Roadmap", to: "/docs#roadmap" },
    ],
  },
  {
    title: "Resources",
    links: [
      { label: "Documentation", to: "/docs" },
      { label: "API reference", to: "/docs#api-audits" },
      { label: "CPI whitepaper", to: "/docs#cpi" },
      { label: "Status", to: "/docs#status" },
    ],
  },
  {
    title: "Company",
    links: [
      { label: "About", to: "/docs#about" },
      { label: "Blog", to: "/docs#blog" },
      { label: "Careers", to: "/docs#careers" },
      { label: "Contact", to: "/signup" },
    ],
  },
  {
    title: "Legal",
    links: [
      { label: "Privacy", to: "/docs#privacy" },
      { label: "Terms", to: "/docs#terms" },
      { label: "DPA", to: "/docs#dpa" },
      { label: "Security", to: "/docs#security" },
    ],
  },
];

export function Footer() {
  return (
    <footer className="border-t border-border/60 bg-card/40">
      <div className="mx-auto w-full max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <div className="grid gap-12 md:grid-cols-[1.4fr_repeat(4,1fr)]">
          <div className="max-w-xs">
            <Logo />
            <p className="mt-4 text-sm text-muted-foreground">
              Explainable Generative Engine Optimization. Citation probability intervals, not
              snapshots.
            </p>
            <div className="mt-6 flex items-center gap-2">
              {[
                { Icon: GitBranch, label: "GitHub" },
                { Icon: AtSign, label: "X / Twitter" },
                { Icon: Rss, label: "Engineering blog" },
              ].map(({ Icon, label }) => (
                <a
                  key={label}
                  href="https://xgeo.dev"
                  target="_blank"
                  rel="noreferrer"
                  aria-label={label}
                  className="grid size-9 place-items-center rounded-lg border border-border/60 text-muted-foreground transition-colors hover:border-border hover:bg-muted/50 hover:text-foreground"
                >
                  <Icon className="size-4" />
                </a>
              ))}
            </div>
          </div>

          {COLUMNS.map((col) => (
            <nav key={col.title} aria-label={col.title}>
              <h3 className="text-xs font-semibold uppercase tracking-[0.14em] text-foreground">
                {col.title}
              </h3>
              <ul className="mt-4 space-y-2.5">
                {col.links.map((link) => (
                  <li key={link.label}>
                    <Link
                      to={link.to}
                      className="text-sm text-muted-foreground transition-colors hover:text-foreground"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </nav>
          ))}
        </div>

        <div className="mt-14 flex flex-col items-start justify-between gap-4 border-t border-border/60 pt-8 sm:flex-row sm:items-center">
          <p className="text-xs text-muted-foreground">
            © {new Date().getFullYear()} X-GEO Labs, Inc. All rights reserved.
          </p>
          <div className="flex items-center gap-4">
            <span className="inline-flex items-center gap-2 text-xs text-muted-foreground">
              <span className="relative flex size-2">
                <span className="absolute inline-flex size-full rounded-full bg-success opacity-60 animate-pulse-ring" />
                <span className="relative inline-flex size-2 rounded-full bg-success" />
              </span>
              All systems normal
            </span>
            <ThemeToggle />
          </div>
        </div>
      </div>
    </footer>
  );
}
