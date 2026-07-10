"use client";

import { Palette, Monitor, Moon, Sun, Check } from "lucide-react";
import { useTheme } from "@hostel/ui";
import { SectionHeader, SettingsPanel } from "../primitives";
import { ComingSoonBadge } from "@/features/account/components/ComingSoon";

type ThemeOption = { id: "light" | "dark" | "system"; label: string; hint: string; icon: React.ComponentType<{ className?: string }> };

const THEMES: ThemeOption[] = [
  { id: "light", label: "Light", hint: "Bright, high-legibility", icon: Sun },
  { id: "dark", label: "Dark", hint: "Easy on the eyes", icon: Moon },
  { id: "system", label: "System", hint: "Match your device", icon: Monitor },
];

/** Appearance settings. Theme is fully live via the app ThemeContext. */
export function AppearanceSection() {
  const { theme, setTheme } = useTheme();

  return (
    <div className="space-y-5">
      <SectionHeader
        icon={Palette}
        title="Appearance"
        description="Personalize how the workspace looks on this device."
        status="partial"
      />

      <SettingsPanel title="Theme" description="Choose a light, dark or system-matched theme." icon={Palette}>
        <div className="grid gap-3 sm:grid-cols-3">
          {THEMES.map((opt) => {
            const active = theme === opt.id;
            const Icon = opt.icon;
            return (
              <button
                key={opt.id}
                type="button"
                onClick={() => setTheme(opt.id)}
                aria-pressed={active}
                className={`group relative flex flex-col items-start gap-3 rounded-2xl border p-4 text-left transition ${
                  active
                    ? "border-[var(--accent)] bg-[color-mix(in_srgb,var(--accent)_8%,transparent)]"
                    : "border-[var(--border)] bg-[var(--card)] hover:border-[var(--border-hover)] hover:bg-[var(--background-secondary)]"
                }`}
              >
                <span
                  className={`grid h-9 w-9 place-items-center rounded-xl ${
                    active ? "bg-[var(--accent)] text-white" : "bg-[var(--background-secondary)] text-[var(--muted)]"
                  }`}
                >
                  <Icon className="h-5 w-5" />
                </span>
                <div>
                  <div className="flex items-center gap-1.5 text-sm font-semibold text-[var(--foreground)]">
                    {opt.label}
                    {active ? <Check className="h-3.5 w-3.5 text-[var(--accent)]" /> : null}
                  </div>
                  <div className="text-xs text-[var(--muted)]">{opt.hint}</div>
                </div>
              </button>
            );
          })}
        </div>
      </SettingsPanel>

      <SettingsPanel title="Interface" description="More display controls are on the way." icon={Palette}>
        <ul className="divide-y divide-[var(--border)]">
          {[
            ["Accent color", "Pick a brand accent for buttons and highlights"],
            ["Density", "Comfortable or compact spacing"],
            ["High contrast", "Maximum legibility for accessibility"],
            ["Reduced motion", "Minimize animations and transitions"],
          ].map(([label, hint]) => (
            <li key={label} className="flex items-center justify-between gap-3 py-3">
              <div>
                <div className="text-sm font-medium text-[var(--foreground)]">{label}</div>
                <div className="text-xs text-[var(--muted)]">{hint}</div>
              </div>
              <ComingSoonBadge />
            </li>
          ))}
        </ul>
      </SettingsPanel>
    </div>
  );
}
