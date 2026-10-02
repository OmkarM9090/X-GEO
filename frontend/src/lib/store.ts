import { create } from "zustand";

export type Theme = "dark" | "light";

const STORAGE_KEY = "xgeo-theme";

function getInitialTheme(): Theme {
  if (typeof window === "undefined") return "dark";
  try {
    return localStorage.getItem(STORAGE_KEY) === "light" ? "light" : "dark";
  } catch {
    return "dark";
  }
}

function applyThemeClass(theme: Theme): void {
  const root = document.documentElement;
  root.classList.add("transition-theme");
  root.classList.toggle("dark", theme === "dark");
  root.style.colorScheme = theme;
  window.setTimeout(() => root.classList.remove("transition-theme"), 450);
}

interface ThemeState {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
}

/** Dark mode is the default; preference persists in localStorage ("xgeo-theme"). */
export const useThemeStore = create<ThemeState>((set, get) => ({
  theme: getInitialTheme(),
  setTheme: (theme) => {
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch {
      /* storage unavailable — still toggle for the session */
    }
    applyThemeClass(theme);
    set({ theme });
  },
  toggleTheme: () => {
    const next: Theme = get().theme === "dark" ? "light" : "dark";
    get().setTheme(next);
  },
}));

interface UIState {
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
  commandOpen: boolean;
  setCommandOpen: (open: boolean) => void;
  /** Demo flag: renders dashboard empty states instead of mock data. */
  mockEmpty: boolean;
  toggleMockEmpty: () => void;
}

export const useUIStore = create<UIState>((set) => ({
  sidebarCollapsed: false,
  toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
  commandOpen: false,
  setCommandOpen: (open) => set({ commandOpen: open }),
  mockEmpty: false,
  toggleMockEmpty: () => set((s) => ({ mockEmpty: !s.mockEmpty })),
}));
