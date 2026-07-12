"use client";

import { Button } from "@hostel/ui";
import { Card } from "@hostel/ui";
import { useToast } from "@hostel/ui";
import { CreditCard, FileText, HardDrive, Sparkles } from "lucide-react";
import { ComingSoonBadge } from "./ComingSoon";

// Placeholder figures — clearly illustrative until billing is wired to a real
// subscription provider. Kept obviously round so nobody mistakes them for live data.
const STORAGE = [
  { label: "Documents", used: 0.4, color: "var(--accent)" },
  { label: "Images", used: 0.2, color: "var(--info)" },
  { label: "Backups", used: 0.1, color: "var(--success)" },
];
const STORAGE_TOTAL_GB = 5;

export function BillingSection() {
  const toast = useToast();
  const notify = () => toast.info("Billing isn't enabled yet — this is a preview of what's coming.");

  const usedGb = STORAGE.reduce((sum, s) => sum + s.used, 0);
  const usedPct = Math.min(100, Math.round((usedGb / STORAGE_TOTAL_GB) * 100));

  return (
    <div className="space-y-4">
      {/* Current plan */}
      <Card>
        <div className="mb-4 flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 text-base font-semibold text-[var(--foreground)]">
            <CreditCard className="h-4 w-4 text-[var(--accent)]" />
            Plan &amp; subscription
          </div>
          <ComingSoonBadge />
        </div>
        <div className="flex flex-col gap-4 rounded-xl bg-[var(--background-secondary)] p-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-lg font-semibold text-[var(--foreground)]">Free</span>
              <span className="rounded-full bg-[var(--success)]/15 px-2 py-0.5 text-[11px] font-semibold text-[var(--success)]">
                Active
              </span>
            </div>
            <p className="mt-0.5 text-sm text-[var(--muted)]">
              You&apos;re on the starter plan. Paid tiers with higher limits are on the way.
            </p>
          </div>
          <Button onClick={notify} className="shrink-0">
            <Sparkles className="h-4 w-4" />
            Upgrade plan
          </Button>
        </div>
      </Card>

      {/* Storage usage */}
      <Card>
        <div className="mb-4 flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 text-base font-semibold text-[var(--foreground)]">
            <HardDrive className="h-4 w-4 text-[var(--accent)]" />
            Storage
          </div>
          <ComingSoonBadge />
        </div>
        <div className="mb-2 flex items-baseline justify-between">
          <span className="text-sm text-[var(--muted)]">
            {usedGb.toFixed(1)} GB of {STORAGE_TOTAL_GB} GB used
          </span>
          <span className="text-sm font-medium text-[var(--foreground)]">{usedPct}%</span>
        </div>
        <div className="flex h-2.5 w-full overflow-hidden rounded-full bg-[var(--border)]">
          {STORAGE.map((s) => (
            <span
              key={s.label}
              style={{ width: `${(s.used / STORAGE_TOTAL_GB) * 100}%`, backgroundColor: s.color }}
            />
          ))}
        </div>
        <div className="mt-3 flex flex-wrap gap-4">
          {STORAGE.map((s) => (
            <span key={s.label} className="inline-flex items-center gap-1.5 text-xs text-[var(--muted)]">
              <span className="h-2 w-2 rounded-full" style={{ backgroundColor: s.color }} />
              {s.label} · {s.used.toFixed(1)} GB
            </span>
          ))}
        </div>
      </Card>

      {/* Invoices */}
      <Card>
        <div className="mb-4 flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 text-base font-semibold text-[var(--foreground)]">
            <FileText className="h-4 w-4 text-[var(--accent)]" />
            Invoices
          </div>
          <ComingSoonBadge />
        </div>
        <div className="rounded-xl border border-dashed border-[var(--border)] bg-[var(--background-secondary)] px-4 py-10 text-center">
          <div className="text-2xl" aria-hidden>
            🧾
          </div>
          <p className="mt-2 text-sm font-medium text-[var(--foreground)]">No invoices yet</p>
          <p className="text-sm text-[var(--muted)]">
            When paid plans launch, your billing history and receipts will appear here.
          </p>
        </div>
      </Card>
    </div>
  );
}
