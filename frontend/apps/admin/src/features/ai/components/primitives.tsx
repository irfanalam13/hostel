"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { AI_SECTIONS } from "../registry";

/** Wraps every AI page: eyebrow + title bar + section pills + content. */
export function AiShell({
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
          AI Assistant
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
        {AI_SECTIONS.map((sec) => {
          const on = sec.href === "/ai" ? pathname === "/ai" : pathname.startsWith(sec.href);
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

      {children}
    </div>
  );
}

export function StatCard({
  label,
  value,
  hint,
}: {
  label: string;
  value: React.ReactNode;
  hint?: string;
}) {
  return (
    <div className="rounded-2xl border border-[var(--border)] bg-[var(--card)] p-4 shadow-[var(--shadow-sm)]">
      <div className="text-[11px] font-medium uppercase tracking-wide text-[var(--muted)]">
        {label}
      </div>
      <div className="mt-1 text-2xl font-semibold text-[var(--foreground)]">{value}</div>
      {hint ? <div className="mt-0.5 text-xs text-[var(--muted)]">{hint}</div> : null}
    </div>
  );
}
