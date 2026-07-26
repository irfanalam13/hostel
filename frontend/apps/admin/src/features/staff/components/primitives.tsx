"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import type { StaffStatus } from "../types/staff.types";
import { STAFF_SECTIONS } from "../registry";

const TONES: Record<string, string> = {
  neutral: "bg-[var(--background-secondary)] text-[var(--foreground-secondary)]",
  accent: "bg-[var(--accent-soft)] text-[var(--accent)]",
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

const STATUS_COLOR: Record<StaffStatus, string> = {
  active: "var(--success)",
  invited: "var(--info)",
  suspended: "var(--warning)",
  disabled: "var(--muted)",
  locked: "var(--error)",
};

export function StatusBadge({ status, label }: { status: StaffStatus; label?: string }) {
  return <Badge color={STATUS_COLOR[status] ?? "var(--muted)"}>{label ?? status}</Badge>;
}

/** A small labelled detail block for profile / form layouts. */
export function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <div className="mb-1 text-sm text-[var(--foreground-secondary)]">{label}</div>
      {children}
    </label>
  );
}

/** Read-only labelled value used on the profile detail page. */
export function ReadField({ label, value }: { label: string; value?: React.ReactNode }) {
  return (
    <div>
      <div className="text-xs uppercase tracking-wide text-[var(--muted)]">{label}</div>
      <div className="mt-0.5 text-sm text-[var(--foreground)]">{value || "—"}</div>
    </div>
  );
}

export function StatCard({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-[var(--border)] bg-[var(--card)] px-4 py-3">
      <div className="text-xs uppercase tracking-wide text-[var(--muted)]">{label}</div>
      <div className="mt-1 text-2xl font-semibold text-[var(--foreground)]">{value}</div>
    </div>
  );
}

/** Wraps every Staff page: title bar + section pills + content. */
export function StaffShell({
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
          Staff Management
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
        {STAFF_SECTIONS.map((sec) => {
          const on =
            sec.href === "/staff" ? pathname === "/staff" : pathname.startsWith(sec.href);
          const Icon = sec.icon;
          return (
            <Link
              key={sec.id}
              href={sec.href}
              className={`inline-flex items-center gap-2 rounded-xl px-3 py-1.5 text-sm font-medium transition ${
                on
                  ? "bg-[var(--accent)] text-white shadow-sm"
                  : "text-[var(--foreground-secondary)] hover:bg-[var(--background-secondary)]"
              }`}
            >
              <Icon className="h-4 w-4" />
              {sec.label}
            </Link>
          );
        })}
      </nav>

      <div>{children}</div>
    </div>
  );
}
