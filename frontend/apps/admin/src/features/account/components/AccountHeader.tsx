"use client";

import { useState } from "react";
import type { AuthUser } from "@/features/auth/api/auth.api";
import { authStore } from "@hostel/auth";
import { useToast } from "@hostel/ui";
import { CalendarDays, Check, Clock, Copy, ShieldCheck } from "lucide-react";
import { avatarGradient, displayName, formatDate, formatDateTime, initials, roleLabel } from "../lib";

export function AccountHeader({ user }: { user: AuthUser | null }) {
  const toast = useToast();
  const name = displayName(user);
  const hostelCode = user?.hostel_code || authStore.getHostelCode() || "—";
  const canCopy = hostelCode !== "—";
  const [copied, setCopied] = useState(false);

  async function copyHostelId() {
    if (!canCopy) return;
    try {
      await navigator.clipboard.writeText(hostelCode);
      setCopied(true);
      toast.success("Hostel ID copied to clipboard.");
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error("Couldn't copy Hostel ID.");
    }
  }

  return (
    <div className="overflow-hidden rounded-[20px] border border-[var(--border)] bg-[var(--card)] shadow-[var(--shadow-sm)]">
      {/* Brand banner */}
      <div
        className="h-24 w-full"
        style={{ background: avatarGradient(user?.username || "account") }}
        aria-hidden
      />

      <div className="px-5 pb-5">
        <div className="-mt-10 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div className="flex items-end gap-4">
            <div
              className="grid h-20 w-20 shrink-0 place-items-center rounded-2xl text-2xl font-bold text-white shadow-[var(--shadow-md)] ring-4 ring-[var(--card)]"
              style={{ background: avatarGradient(user?.username || "account") }}
            >
              {initials(user)}
            </div>
            <div className="pb-1">
              <h2 className="text-xl font-semibold tracking-tight text-[var(--foreground)]">{name}</h2>
              <p className="text-sm text-[var(--muted)]">@{user?.username || "—"}</p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2 pb-1">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-[var(--accent-soft)] px-3 py-1 text-xs font-semibold text-[var(--accent)]">
              <ShieldCheck className="h-3.5 w-3.5" />
              {roleLabel(user?.role)}
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-[var(--border)] bg-[var(--background-secondary)] py-1 pl-3 pr-1 text-xs font-medium text-[var(--foreground-secondary)]">
              Hostel ID <span className="font-mono font-semibold text-[var(--foreground)]">{hostelCode}</span>
              <button
                type="button"
                onClick={copyHostelId}
                disabled={!canCopy}
                aria-label="Copy Hostel ID"
                title="Copy Hostel ID"
                className="grid h-6 w-6 shrink-0 place-items-center rounded-full text-[var(--muted)] transition hover:bg-[var(--card)] hover:text-[var(--foreground)] disabled:cursor-not-allowed disabled:opacity-40"
              >
                {copied ? <Check className="h-3.5 w-3.5 text-[var(--accent)]" /> : <Copy className="h-3.5 w-3.5" />}
              </button>
            </span>
          </div>
        </div>

        {/* Meta row */}
        <div className="mt-5 grid gap-3 border-t border-[var(--border)] pt-4 sm:grid-cols-3">
          <Meta icon={<CalendarDays className="h-4 w-4" />} label="Member since" value={formatDate(user?.date_joined)} />
          <Meta icon={<Clock className="h-4 w-4" />} label="Last sign-in" value={formatDateTime(user?.last_login)} />
          <Meta
            icon={<ShieldCheck className="h-4 w-4" />}
            label="Status"
            value={user?.is_active === false ? "Inactive" : "Active"}
          />
        </div>
      </div>
    </div>
  );
}

function Meta({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="flex items-center gap-3">
      <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-[var(--background-secondary)] text-[var(--muted)]">
        {icon}
      </span>
      <div className="min-w-0">
        <div className="text-[11px] font-semibold uppercase tracking-wider text-[var(--muted)]">{label}</div>
        <div className="truncate text-sm font-medium text-[var(--foreground)]">{value}</div>
      </div>
    </div>
  );
}
