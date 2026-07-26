"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { ACCOUNTING_SECTIONS } from "../registry";
import type { Money as MoneyValue } from "../types/accounting.types";

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

/**
 * Maps every status string used across the accounting entities (journals,
 * periods, fiscal years, fixed assets) to a semantic tone. Anything unmapped
 * falls back to muted.
 */
const STATUS_TONE: Record<string, string> = {
  // success
  posted: "var(--success)",
  approved: "var(--success)",
  active: "var(--success)",
  reconciled: "var(--success)",
  balanced: "var(--success)",
  // warning
  submitted: "var(--warning)",
  draft: "var(--warning)",
  pending: "var(--warning)",
  // error
  disposed: "var(--error)",
  unbalanced: "var(--error)",
  // muted (neutral / terminal)
  reversed: "var(--muted)",
  closed: "var(--muted)",
  fully_depreciated: "var(--muted)",
  inactive: "var(--muted)",
};

const titleize = (s: string) => s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

export function StatusBadge({ status, label }: { status: string; label?: string }) {
  return <Badge color={STATUS_TONE[status] ?? "var(--muted)"}>{label ?? titleize(status)}</Badge>;
}

/** A small labelled detail block for form layouts. */
export function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <div className="mb-1 text-sm text-[var(--foreground-secondary)]">{label}</div>
      {children}
    </label>
  );
}

/** Read-only labelled value used on detail pages. */
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
 * Formats a decimal-string (or number) money value with thousands separators
 * and two decimals. The default currency "NPR" is shown as "Rs."; any other
 * currency code is used verbatim as the prefix.
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

/** Wraps every Accounting page: eyebrow + title bar + section pills + content. */
export function AccountingShell({
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
          Accounting
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
        {ACCOUNTING_SECTIONS.map((sec) => {
          const on =
            sec.href === "/accounting"
              ? pathname === "/accounting"
              : pathname.startsWith(sec.href);
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

/** Shared constant lists reused across accounting forms. */
export const ACCOUNT_TYPES: { value: string; label: string }[] = [
  { value: "asset", label: "Asset" },
  { value: "liability", label: "Liability" },
  { value: "equity", label: "Equity" },
  { value: "income", label: "Income" },
  { value: "expense", label: "Expense" },
];

export const JOURNAL_TYPES: { value: string; label: string }[] = [
  { value: "manual", label: "Manual" },
  { value: "automatic", label: "Automatic" },
  { value: "recurring", label: "Recurring" },
  { value: "adjustment", label: "Adjustment" },
  { value: "opening", label: "Opening" },
  { value: "closing", label: "Closing" },
  { value: "reversal", label: "Reversal" },
  { value: "depreciation", label: "Depreciation" },
];

export const JOURNAL_STATUSES: { value: string; label: string }[] = [
  { value: "draft", label: "Draft" },
  { value: "submitted", label: "Submitted" },
  { value: "approved", label: "Approved" },
  { value: "posted", label: "Posted" },
  { value: "reversed", label: "Reversed" },
];

export const TAX_TYPES: { value: string; label: string }[] = [
  { value: "vat", label: "VAT" },
  { value: "gst", label: "GST" },
  { value: "sales", label: "Sales" },
  { value: "service", label: "Service" },
  { value: "withholding", label: "Withholding" },
  { value: "income", label: "Income" },
  { value: "local", label: "Local" },
  { value: "custom", label: "Custom" },
];

export const DEPRECIATION_METHODS: { value: string; label: string }[] = [
  { value: "straight_line", label: "Straight Line" },
  { value: "declining_balance", label: "Declining Balance" },
  { value: "none", label: "None" },
];

export const BUDGET_PERIOD_TYPES: { value: string; label: string }[] = [
  { value: "annual", label: "Annual" },
  { value: "quarterly", label: "Quarterly" },
  { value: "monthly", label: "Monthly" },
];
