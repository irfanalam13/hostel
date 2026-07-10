"use client";

import React from "react";
import {
  Smartphone,
  Tablet,
  Monitor,
  Download,
  WifiOff,
  Zap,
  Check,
} from "lucide-react";
import { usePwa } from "@hostel/pwa";
import { Section } from "../components/Section";
import { Reveal } from "../components/Reveal";
import { usePlatform, manualInstallSteps, type DeviceType } from "../hooks/usePlatform";

const BENEFITS = [
  { icon: WifiOff, text: "Full offline access — keep working through outages" },
  { icon: Zap, text: "Instant load, native-like speed on any device" },
  { icon: Smartphone, text: "Add to home screen — no app store needed" },
];

const DEVICES: { type: DeviceType; icon: typeof Smartphone; label: string }[] = [
  { type: "mobile", icon: Smartphone, label: "Mobile" },
  { type: "tablet", icon: Tablet, label: "Tablet" },
  { type: "desktop", icon: Monitor, label: "Desktop" },
];

export function PwaSection() {
  // Single source of truth for install state, shared with the navbar button.
  const { isInstallable, isInstalled, installApp } = usePwa();
  // Auto-detect the visitor's device/OS to tailor the install guidance.
  const platform = usePlatform();

  const ActiveIcon =
    DEVICES.find((d) => d.type === platform.type)?.icon ?? Monitor;

  return (
    <Section tone="accent-soft" width="wide">
      <div className="grid items-center gap-10 lg:grid-cols-2">
        <Reveal>
          <div>
            <p className="mb-3 text-sm font-semibold uppercase tracking-wide text-[var(--accent)]">
              Progressive Web App
            </p>
            <h2 className="text-balance text-3xl font-bold tracking-tight text-[var(--foreground)] sm:text-4xl">
              Install once. Works everywhere — even offline.
            </h2>
            <p className="mt-4 text-pretty text-lg leading-relaxed text-[var(--foreground-secondary)]">
              Run your hostel from a phone, tablet or desktop. Install the app to
              your home screen and keep operating when the connection drops —
              everything syncs automatically when you&apos;re back online.
            </p>

            {/* Auto-detected device indicator */}
            {platform.mounted && platform.label && (
              <p className="mt-5 inline-flex items-center gap-2 rounded-full border border-[var(--border)] bg-[var(--card)] px-3 py-1.5 text-xs font-medium text-[var(--foreground-secondary)]">
                <ActiveIcon className="h-4 w-4 text-[var(--accent)]" aria-hidden />
                Detected: <span className="capitalize text-[var(--foreground)]">{platform.label}</span>
              </p>
            )}

            <ul className="mt-6 space-y-3">
              {BENEFITS.map(({ icon: Icon, text }) => (
                <li key={text} className="flex items-start gap-3 text-[var(--foreground)]">
                  <span className="mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-lg bg-[var(--card)] text-[var(--accent)]">
                    <Icon className="h-4 w-4" aria-hidden />
                  </span>
                  <span className="text-sm leading-relaxed">{text}</span>
                </li>
              ))}
            </ul>

            {/* Action area: installed → installable (native) → platform steps */}
            <div className="mt-8">
              {isInstalled ? (
                <span className="inline-flex items-center gap-2 rounded-xl border border-[var(--border)] bg-[var(--card)] px-5 py-3 text-sm font-semibold text-[var(--success)]">
                  <Check className="h-4.5 w-4.5" aria-hidden /> App installed
                </span>
              ) : isInstallable ? (
                <button
                  type="button"
                  onClick={() => void installApp()}
                  className="inline-flex items-center gap-2 rounded-xl bg-[var(--accent)] px-6 py-3 text-base font-semibold text-white shadow-[var(--shadow-md)] transition hover:bg-[var(--accent-hover)] focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[color-mix(in_srgb,var(--accent)_25%,transparent)]"
                >
                  <Download className="h-4.5 w-4.5" aria-hidden /> Install the app
                </button>
              ) : platform.mounted ? (
                <div className="rounded-2xl border border-[var(--border)] bg-[var(--card)] p-5">
                  <p className="text-sm font-semibold text-[var(--foreground)]">
                    Install on your {platform.type}
                  </p>
                  <ol className="mt-3 space-y-2">
                    {manualInstallSteps(platform.os).map((step, i) => (
                      <li key={step} className="flex items-start gap-3 text-sm text-[var(--foreground-secondary)]">
                        <span className="grid h-5 w-5 shrink-0 place-items-center rounded-full bg-[var(--accent-soft)] text-[11px] font-bold text-[var(--accent)]">
                          {i + 1}
                        </span>
                        {step}
                      </li>
                    ))}
                  </ol>
                </div>
              ) : null}
            </div>

            {/* Cross-platform availability, current device highlighted */}
            <div className="mt-6 flex flex-wrap gap-2">
              {DEVICES.map(({ type, icon: Icon, label }) => {
                const active = platform.mounted && platform.type === type;
                return (
                  <span
                    key={type}
                    className={`inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium transition ${
                      active
                        ? "border-[var(--accent)] bg-[var(--accent-soft)] text-[var(--accent)]"
                        : "border-[var(--border)] bg-[var(--card)] text-[var(--foreground-secondary)]"
                    }`}
                  >
                    <Icon className="h-4 w-4" aria-hidden />
                    {label}
                    {active && <span className="ml-0.5 text-[10px]">• you</span>}
                  </span>
                );
              })}
            </div>
          </div>
        </Reveal>

        <Reveal delay={120}>
          <div className="mx-auto w-full max-w-xs">
            {/* Stylised phone frame (decorative). */}
            <div className="rounded-[2.5rem] border-8 border-[var(--foreground)]/90 bg-[var(--card)] p-3 shadow-[var(--shadow-lg)]">
              <div className="rounded-[1.8rem] bg-[var(--background)] p-4">
                <div className="flex items-center gap-2">
                  <span className="grid h-8 w-8 place-items-center rounded-lg bg-[var(--accent)] text-white">
                    <Smartphone className="h-4 w-4" aria-hidden />
                  </span>
                  <span className="text-sm font-semibold text-[var(--foreground)]">Dashboard</span>
                  <span className="ml-auto inline-flex items-center gap-1 rounded-full bg-[var(--accent-soft)] px-2 py-0.5 text-[10px] font-medium text-[var(--accent)]">
                    <WifiOff className="h-3 w-3" aria-hidden /> Offline
                  </span>
                </div>
                <div className="mt-4 space-y-3">
                  {[80, 60, 45].map((w, i) => (
                    <div key={i} className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-3">
                      <div className="h-2 w-16 rounded-full bg-[var(--background-secondary)]" />
                      <div className="mt-2 h-2 rounded-full bg-[var(--accent)]" style={{ width: `${w}%` }} />
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </Reveal>
      </div>
    </Section>
  );
}
