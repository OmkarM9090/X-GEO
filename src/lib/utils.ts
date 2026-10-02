import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/** Tailwind-aware className combiner (shadcn convention). */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

/** 0.62 -> "62%" */
export function formatPercent(value: number, decimals = 0): string {
  return `${(value * 100).toFixed(decimals)}`;
}

/** 0.041 -> "+4.1pp" */
export function formatPoints(delta: number, decimals = 1): string {
  const sign = delta >= 0 ? "+" : "−";
  return `${sign}${Math.abs(delta * 100).toFixed(decimals)}pp`;
}

/** 1248 -> "1,248" */
export function formatNumber(value: number): string {
  return new Intl.NumberFormat("en-US").format(value);
}

/** Deterministic pseudo-random in [0, 1) from an integer seed. */
export function seededRandom(seed: number): number {
  const x = Math.sin(seed * 127.1 + 311.7) * 43758.5453;
  return x - Math.floor(x);
}
