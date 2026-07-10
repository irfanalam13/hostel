"use client";

import React from "react";
import { Sparkles } from "lucide-react";
import { STATUS_META, type SectionStatus, type SettingsSection } from "../registry";

type IconType = React.ComponentType<{ className?: string }>;

/** Small coloured pill communicating a section's maturity. */
export function StatusPill({ status, className = "" }: { status: SectionStatus; className?: string }) {
  const meta = STATUS_META[status];
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${className}`}
      style={{ color: meta.tone, backgroundColor: `color-mix(in srgb, ${meta.tone} 14%, transparent)` }}
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: meta.tone }} aria-hidden />
      {meta.label}
    </span>
  );
}

/**
 * Standard header for a settings section: icon + title + description, with an
 * optional status pill and right-aligned actions slot.
 */
export function SectionHeader({
  icon: Icon,
  title,
  description,
  status,
  actions,
}: {
  icon: IconType;
  title: string;
  description?: string;
  status?: SectionStatus;
  actions?: React.ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div className="flex items-start gap-3">
        <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-[color-mix(in_srgb,var(--accent)_12%,transparent)] text-[var(--accent)]">
          <Icon className="h-5 w-5" />
        </span>
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-semibold text-[var(--foreground)]">{title}</h2>
            {status ? <StatusPill status={status} /> : null}
          </div>
          {description ? (
            <p className="mt-0.5 max-w-2xl text-sm text-[var(--muted)]">{description}</p>
          ) : null}
        </div>
      </div>
      {actions ? <div className="flex items-center gap-2">{actions}</div> : null}
    </div>
  );
}

/**
 * A titled settings card. Use for grouping related controls inside a section.
 * Falls back to a plain container when no title is given.
 */
export function SettingsPanel({
  title,
  description,
  icon: Icon,
  badge,
  footer,
  children,
  className = "",
}: {
  title?: string;
  description?: string;
  icon?: IconType;
  badge?: React.ReactNode;
  footer?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section
      className={`overflow-hidden rounded-[20px] border border-[var(--border)] bg-[var(--card)] shadow-[var(--shadow-sm)] ${className}`}
    >
      {title ? (
        <header className="flex items-center justify-between gap-2 border-b border-[var(--border)] px-5 py-4">
          <div className="flex items-center gap-2.5">
            {Icon ? <Icon className="h-4 w-4 text-[var(--accent)]" /> : null}
            <div>
              <h3 className="text-sm font-semibold text-[var(--foreground)]">{title}</h3>
              {description ? <p className="text-xs text-[var(--muted)]">{description}</p> : null}
            </div>
          </div>
          {badge}
        </header>
      ) : null}
      <div className="p-5">{children}</div>
      {footer ? (
        <footer className="border-t border-[var(--border)] bg-[var(--background-secondary)] px-5 py-3">
          {footer}
        </footer>
      ) : null}
    </section>
  );
}

/** Compact metric tile for dashboards. */
export function StatTile({
  label,
  value,
  hint,
  icon: Icon,
  tone = "var(--accent)",
}: {
  label: string;
  value: React.ReactNode;
  hint?: React.ReactNode;
  icon?: IconType;
  tone?: string;
}) {
  return (
    <div className="rounded-[18px] border border-[var(--border)] bg-[var(--card)] p-4 shadow-[var(--shadow-sm)] transition duration-200 hover:-translate-y-0.5 hover:border-[var(--border-hover)] hover:shadow-[var(--shadow-md)]">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-[var(--muted)]">{label}</span>
        {Icon ? (
          <span
            className="grid h-7 w-7 place-items-center rounded-lg"
            style={{ color: tone, backgroundColor: `color-mix(in srgb, ${tone} 14%, transparent)` }}
          >
            <Icon className="h-4 w-4" />
          </span>
        ) : null}
      </div>
      <div className="mt-2 text-xl font-semibold text-[var(--foreground)]">{value}</div>
      {hint ? <div className="mt-0.5 text-xs text-[var(--muted)]">{hint}</div> : null}
    </div>
  );
}

/** A single key/value line for definition-style detail cards. */
export function DetailRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 py-2 text-sm">
      <span className="text-[var(--muted)]">{label}</span>
      <span className="font-medium text-[var(--foreground)]">{children}</span>
    </div>
  );
}

/**
 * Designed empty-state for sections that are on the roadmap but not yet wired.
 * Reads the section's own description + roadmap from the registry.
 */
export function PlaceholderSection({ section }: { section: SettingsSection }) {
  const Icon = section.icon;
  return (
    <div className="space-y-5">
      <SectionHeader icon={Icon} title={section.label} description={section.description} status={section.status} />
      <div className="rounded-[20px] border border-dashed border-[var(--border)] bg-[var(--card)] px-6 py-12 text-center shadow-[var(--shadow-sm)]">
        <span className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-[color-mix(in_srgb,var(--accent)_10%,transparent)] text-[var(--accent)]">
          <Icon className="h-7 w-7" />
        </span>
        <div className="mt-4 flex items-center justify-center gap-2">
          <h3 className="text-base font-semibold text-[var(--foreground)]">{section.label} is coming soon</h3>
          <span className="inline-flex items-center gap-1 rounded-full border border-[var(--border)] bg-[var(--background-secondary)] px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)]">
            <Sparkles className="h-3 w-3" />
            Planned
          </span>
        </div>
        <p className="mx-auto mt-1 max-w-md text-sm text-[var(--muted)]">
          This area is part of the enterprise settings roadmap. The experience is designed and will be wired up in an
          upcoming increment.
        </p>
        {section.roadmap && section.roadmap.length > 0 ? (
          <ul className="mx-auto mt-5 grid max-w-md gap-2 text-left">
            {section.roadmap.map((item) => (
              <li
                key={item}
                className="flex items-center gap-2 rounded-xl border border-[var(--border)] bg-[var(--background-secondary)] px-3 py-2 text-sm text-[var(--foreground-secondary)]"
              >
                <span className="h-1.5 w-1.5 rounded-full bg-[var(--accent)]" aria-hidden />
                {item}
              </li>
            ))}
          </ul>
        ) : null}
      </div>
    </div>
  );
}
