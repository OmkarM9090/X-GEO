import type { Config } from "tailwindcss";

/**
 * X-GEO design system — Tailwind wiring.
 * Raw values live in src/styles/tokens.css as CSS variables (dual theme).
 * This config maps those variables to utilities (shadcn-compatible).
 * Loaded from src/styles/globals.css via `@config` (Tailwind v4 engine).
 */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border) / <alpha-value>)",
        input: "hsl(var(--border) / <alpha-value>)",
        ring: "hsl(var(--accent) / <alpha-value>)",
        background: "hsl(var(--background) / <alpha-value>)",
        foreground: "hsl(var(--foreground) / <alpha-value>)",
        primary: {
          DEFAULT: "hsl(var(--primary) / <alpha-value>)",
          foreground: "hsl(var(--primary-foreground) / <alpha-value>)",
        },
        secondary: {
          DEFAULT: "hsl(var(--muted) / <alpha-value>)",
          foreground: "hsl(var(--foreground) / <alpha-value>)",
        },
        muted: {
          DEFAULT: "hsl(var(--muted) / <alpha-value>)",
          foreground: "hsl(var(--muted-foreground) / <alpha-value>)",
        },
        card: {
          DEFAULT: "hsl(var(--card) / <alpha-value>)",
          foreground: "hsl(var(--card-foreground) / <alpha-value>)",
        },
        surface: {
          raised: "hsl(var(--surface-raised) / <alpha-value>)",
          overlay: "hsl(var(--surface-overlay) / <alpha-value>)",
        },
        popover: {
          DEFAULT: "hsl(var(--card) / <alpha-value>)",
          foreground: "hsl(var(--card-foreground) / <alpha-value>)",
        },
        accent: {
          DEFAULT: "hsl(var(--accent) / <alpha-value>)",
          foreground: "hsl(var(--accent-foreground) / <alpha-value>)",
          glow: "hsl(var(--accent-glow) / <alpha-value>)",
        },
        success: "hsl(var(--success) / <alpha-value>)",
        warning: "hsl(var(--warning) / <alpha-value>)",
        danger: "hsl(var(--danger) / <alpha-value>)",
        "chart-1": "hsl(var(--chart-1) / <alpha-value>)",
        "chart-2": "hsl(var(--chart-2) / <alpha-value>)",
        "chart-3": "hsl(var(--chart-3) / <alpha-value>)",
        "chart-4": "hsl(var(--chart-4) / <alpha-value>)",
        "chart-5": "hsl(var(--chart-5) / <alpha-value>)",
      },
      fontFamily: {
        sans: ["Geist Local", "Geist", "Inter", "system-ui", "-apple-system", "sans-serif"],
        heading: ["Geist Local", "Geist", "Inter", "system-ui", "sans-serif"],
        mono: ["Geist Mono Local", "Geist Mono", "JetBrains Mono", "ui-monospace", "monospace"],
      },
      fontSize: {
        hero: ["clamp(2.625rem, 6.5vw, 4.5rem)", { lineHeight: "1.05", letterSpacing: "-0.02em", fontWeight: "600" }],
        display: ["clamp(2.125rem, 4.5vw, 3.5rem)", { lineHeight: "1.1", letterSpacing: "-0.02em", fontWeight: "600" }],
        h1: ["clamp(1.875rem, 3.5vw, 2.5rem)", { lineHeight: "1.15", letterSpacing: "-0.02em", fontWeight: "600" }],
        h2: ["clamp(1.5rem, 2.75vw, 2rem)", { lineHeight: "1.2", letterSpacing: "-0.02em", fontWeight: "600" }],
        h3: ["1.5rem", { lineHeight: "1.3", letterSpacing: "-0.02em", fontWeight: "600" }],
        "body-lg": ["1.125rem", { lineHeight: "1.6", fontWeight: "400" }],
        body: ["1rem", { lineHeight: "1.6", fontWeight: "400" }],
        sm: ["0.875rem", { lineHeight: "1.5", fontWeight: "400" }],
        xs: ["0.75rem", { lineHeight: "1.4", fontWeight: "500" }],
      },
      borderRadius: {
        sm: "4px",
        md: "6px",
        lg: "8px",
        xl: "12px",
        "2xl": "16px",
      },
      boxShadow: {
        card: "0 8px 32px -12px rgba(0, 0, 0, 0.28)",
        "card-hover": "0 16px 48px -12px rgba(0, 0, 0, 0.42)",
        glow: "0 0 60px -15px hsl(var(--accent-glow) / 0.55)",
        "glow-sm": "0 0 32px -12px hsl(var(--accent-glow) / 0.5)",
      },
      transitionTimingFunction: {
        "out-expo": "cubic-bezier(0.16, 1, 0.3, 1)",
        "theme-morph": "cubic-bezier(0.4, 0, 0.2, 1)",
      },
      maxWidth: {
        "8xl": "1280px",
      },
    },
  },
  plugins: [],
} satisfies Config;
