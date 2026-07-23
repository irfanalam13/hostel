"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { INVENTORY_SECTIONS } from "../registry";
import type { Money as MoneyValue } from "../types/inventory.types";

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

/** Maps inventory/asset/PO/movement status strings to a semantic tone. */
const STATUS_TONE: Record<string, string> = {
  // success
  available: "var(--success)",
  approved: "var(--success)",
  fully_received: "var(--success)",
  active: "var(--success)",
  new: "var(--success)",
  good: "var(--success)",
  in: "var(--success)",
  // accent
  assigned: "var(--accent)",
  ordered: "var(--accent)",
  // warning
  draft: "var(--warning)",
  pending_approval: "var(--warning)",
  partially_received: "var(--warning)",
  in_maintenance: "var(--warning)",
  low: "var(--warning)",
  fair: "var(--warning)",
  // error
  cancelled: "var(--error)",
  damaged: "var(--error)",
  lost: "var(--error)",
  out_of_stock: "var(--error)",
  poor: "var(--error)",
  out: "var(--error)",
  // muted
  closed: "var(--muted)",
  retired: "var(--muted)",
  disposed: "var(--muted)",
  unusable: "var(--muted)",
};

const titleize = (s: string) => s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

export function StatusBadge({ status, label }: { status: string; label?: string }) {
  return <Badge color={STATUS_TONE[status] ?? "var(--muted)"}>{label ?? titleize(status)}</Badge>;
}

export function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <div className="mb-1 text-sm text-[var(--foreground-secondary)]">{label}</div>
      {children}
    </label>
  );
}

export function ReadField({ label, value }: { label: string; value?: React.ReactNode }) {
  return (
    <div>
      <div className="text-xs uppercase tracking-wide text-[var(--muted)]">{label}</div>
      <div className="mt-0.5 text-sm text-[var(--foreground)]">{value || "—"}</div>
    </div>
  );
}

export function StatCard({
  label,
  value,
  tone,
  hint,
}: {
  label: string;
  value: React.ReactNode;
  tone?: "success" | "warning" | "error" | "accent";
  hint?: React.ReactNode;
}) {
  const color =
    tone === "success"
      ? "var(--success)"
      : tone === "warning"
        ? "var(--warning)"
        : tone === "error"
          ? "var(--error)"
          : tone === "accent"
            ? "var(--accent)"
            : "var(--foreground)";
  return (
    <div className="rounded-2xl border border-[var(--border)] bg-[var(--card)] px-4 py-3">
      <div className="text-xs uppercase tracking-wide text-[var(--muted)]">{label}</div>
      <div className="mt-1 text-2xl font-semibold" style={{ color }}>
        {value}
      </div>
      {hint ? <div className="mt-0.5 text-xs text-[var(--muted)]">{hint}</div> : null}
    </div>
  );
}

/**
 * Formats a decimal-string (or number) money value. The default currency "NPR"
 * is shown as "Rs."; any other currency code is used verbatim as the prefix.
 */
export function formatMoney(value: MoneyValue | number | null | undefined, currency = "NPR"): string {
  const n = typeof value === "number" ? value : parseFloat(value ?? "0");
  const safe = Number.isFinite(n) ? n : 0;
  const symbol = !currency || currency === "NPR" ? "Rs." : currency;
  return `${symbol} ${safe.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

/** Formats a decimal quantity string, trimming trailing zeros. */
export function formatQty(value: string | number | null | undefined): string {
  const n = typeof value === "number" ? value : parseFloat(value ?? "0");
  const safe = Number.isFinite(n) ? n : 0;
  return safe.toLocaleString(undefined, { maximumFractionDigits: 3 });
}

export function Money({
  value,
  currency,
  className = "",
}: {
  value: MoneyValue | number | null | undefined;
  currency?: string;
  className?: string;
}) {
  return <span className={className}>{formatMoney(value, currency)}</span>;
}

/** Wraps every Inventory page: eyebrow + title bar + section pills + content. */
export function InventoryShell({
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
          Inventory & Asset Management
        </div>
        <div className="mt-1 flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold text-[var(--foreground)]">{title}</h1>
            {description ? <p className="mt-0.5 text-sm text-[var(--muted)]">{description}</p> : null}
          </div>
          {actions ? <div className="flex items-center gap-2">{actions}</div> : null}
        </div>
      </div>

      <nav className="flex flex-wrap gap-1.5">
        {INVENTORY_SECTIONS.map((sec) => {
          const on =
            sec.href === "/inventory" ? pathname === "/inventory" : pathname.startsWith(sec.href);
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

export const cardClass =
  "rounded-[20px] border border-[var(--border)] bg-[var(--card)] p-5 shadow-[var(--shadow-sm)]";
