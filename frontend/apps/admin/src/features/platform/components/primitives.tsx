"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { PLATFORM_SECTIONS } from "../registry";

/** A pill toggle switch. */
export function Toggle({
  checked,
  onChange,
  disabled,
  label,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  disabled?: boolean;
  label?: string;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition disabled:cursor-not-allowed disabled:opacity-50 ${
        checked ? "bg-[var(--accent)]" : "bg-[var(--border)]"
      }`}
    >
      <span
        className={`inline-block h-5 w-5 transform rounded-full bg-white shadow transition ${
          checked ? "translate-x-5" : "translate-x-0.5"
        }`}
      />
    </button>
  );
}

const TONES: Record<string, string> = {
  neutral: "bg-[var(--background-secondary)] text-[var(--foreground-secondary)]",
  accent: "bg-[var(--accent-soft)] text-[var(--accent)]",
  success: "text-white",
  warning: "text-white",
  info: "text-white",
};

export function Badge({
  children,
  tone = "neutral",
  color,
}: {
  children: React.ReactNode;
  tone?: keyof typeof TONES | string;
  color?: string;
}) {
  const style = color ? { backgroundColor: color, color: "#fff" } : undefined;
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold ${
        color ? "" : TONES[tone] ?? TONES.neutral
      }`}
      style={style}
    >
      {children}
    </span>
  );
}

export function Tabs({
  tabs,
  active,
  onChange,
}: {
  tabs: { id: string; label: string; count?: number }[];
  active: string;
  onChange: (id: string) => void;
}) {
  return (
    <div className="flex flex-wrap gap-1 border-b border-[var(--border)]">
      {tabs.map((t) => {
        const on = t.id === active;
        return (
          <button
            key={t.id}
            type="button"
            onClick={() => onChange(t.id)}
            className={`-mb-px border-b-2 px-4 py-2 text-sm font-medium transition ${
              on
                ? "border-[var(--accent)] text-[var(--foreground)]"
                : "border-transparent text-[var(--muted)] hover:text-[var(--foreground)]"
            }`}
          >
            {t.label}
            {typeof t.count === "number" ? (
              <span className="ml-1.5 text-xs text-[var(--muted)]">{t.count}</span>
            ) : null}
          </button>
        );
      })}
    </div>
  );
}

/** Wraps every platform page: title bar + section pills + content. */
export function PlatformShell({
  title,
  description,
  actions,
  children,
}: {
  title: string;
  description?: string;
  actions?: React.ReactNode;
  children: React.ReactNode;
}) {
  const pathname = usePathname() || "";

  return (
    <div className="mx-auto max-w-6xl p-4 sm:p-6 space-y-5">
      <div>
        <div className="text-[11px] font-semibold uppercase tracking-wide text-[var(--accent)]">
          Platform · Super Admin
        </div>
        <div className="mt-1 flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold text-[var(--foreground)]">{title}</h1>
            {description ? (
              <p className="mt-0.5 text-sm text-[var(--muted)]">{description}</p>
            ) : null}
          </div>
          {actions ? <div className="flex items-center gap-2">{actions}</div> : null}
        </div>
      </div>

      <nav className="flex flex-wrap gap-1.5">
        {PLATFORM_SECTIONS.map((s) => {
          const on =
            s.href === "/platform"
              ? pathname === "/platform"
              : pathname.startsWith(s.href);
          const Icon = s.icon;
          return (
            <Link
              key={s.id}
              href={s.href}
              className={`inline-flex items-center gap-2 rounded-xl px-3 py-1.5 text-sm font-medium transition ${
                on
                  ? "bg-[var(--accent)] text-white shadow-sm"
                  : "text-[var(--foreground-secondary)] hover:bg-[var(--background-secondary)]"
              }`}
            >
              <Icon className="h-4 w-4" />
              {s.label}
            </Link>
          );
        })}
      </nav>

      <div>{children}</div>
    </div>
  );
}

/** Small labelled stat/detail block. */
export function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <div className="mb-1 text-sm text-[var(--foreground-secondary)]">{label}</div>
      {children}
    </label>
  );
}
