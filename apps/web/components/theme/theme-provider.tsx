"use client";

import * as React from "react";
import { create } from "zustand";

type Theme = "dark" | "light";

interface ThemeStore {
  theme: Theme;
  setTheme: (t: Theme) => void;
  toggle: () => void;
}

function getInitialTheme(): Theme {
  if (typeof window === "undefined") return "dark";
  const stored = window.localStorage.getItem("automind-theme");
  return stored === "light" || stored === "dark" ? stored : "dark";
}

export const useThemeStore = create<ThemeStore>((set, get) => ({
  theme: "dark",
  setTheme: (t) => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem("automind-theme", t);
    }
    set({ theme: t });
  },
  toggle: () => get().setTheme(get().theme === "dark" ? "light" : "dark"),
}));

interface ThemeProviderProps {
  attribute: string;
  defaultTheme: Theme;
  enableSystem?: boolean;
  disableTransitionOnChange?: boolean;
  children: React.ReactNode;
}

export function ThemeProvider({
  attribute,
  defaultTheme,
  children,
}: ThemeProviderProps) {
  const theme = useThemeStore((s) => s.theme);
  const setTheme = useThemeStore((s) => s.setTheme);

  React.useEffect(() => {
    const initial = getInitialTheme();
    setTheme(initial);
  }, [setTheme]);

  React.useEffect(() => {
    const root = document.documentElement;
    root.classList.remove("light", "dark");
    root.classList.add(theme);
    root.style.colorScheme = theme;
    root.setAttribute(attribute, theme);
  }, [theme, attribute]);

  // SSR-safe default
  React.useEffect(() => {
    document.documentElement.classList.add(defaultTheme);
  }, [defaultTheme]);

  return <>{children}</>;
}
