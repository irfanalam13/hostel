"use client";

import React from "react";
import { Smartphone, Download, WifiOff, Zap, Check } from "lucide-react";
import { usePwa } from "@/shared/providers/PwaProvider";
import { Section } from "../components/Section";
import { Reveal } from "../components/Reveal";

const BENEFITS = [
  { icon: WifiOff, text: "Full offline access — keep working through outages" },
  { icon: Zap, text: "Instant load, native-like speed on any device" },
  { icon: Smartphone, text: "Add to home screen — no app store needed" },
];

export function PwaSection() {
  // Single source of truth for install state, shared with the navbar button.
  const { isInstallable, isInstalled, installApp } = usePwa();

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
              ) : (
                <p className="text-sm text-[var(--foreground-secondary)]">
                  Open this site in your browser&apos;s menu and choose{" "}
                  <span className="font-semibold text-[var(--foreground)]">
                    &ldquo;Add to Home Screen&rdquo;
                  </span>{" "}
                  to install.
                </p>
              )}
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
