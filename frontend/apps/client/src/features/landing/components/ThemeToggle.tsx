"use client";

import React from "react";
import { Moon, Sun, Monitor } from "lucide-react";
import { useTheme } from "@hostel/ui";

const NEXT_LABEL: Record<string, string> = {
  light: "Switch to dark theme",
  dark: "Switch to system theme",
  system: "Switch to light theme",
};

/** Cycles light → dark → system, reusing the app-wide ThemeContext. */
export function ThemeToggle({ className = "" }: { className?: string }) {
  const { theme, toggleTheme } = useTheme();

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={NEXT_LABEL[theme] ?? "Toggle theme"}
      title={NEXT_LABEL[theme] ?? "Toggle theme"}
      className={`grid h-9 w-9 place-items-center rounded-xl border border-[var(--border)] bg-[var(--card)] text-[var(--foreground-secondary)] transition hover:border-[var(--border-hover)] hover:text-[var(--foreground)] focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[color-mix(in_srgb,var(--accent)_18%,transparent)] ${className}`}
    >
      {theme === "light" && <Sun className="h-4.5 w-4.5" aria-hidden />}
      {theme === "dark" && <Moon className="h-4.5 w-4.5" aria-hidden />}
      {theme === "system" && <Monitor className="h-4.5 w-4.5" aria-hidden />}
    </button>
  );
}
