"use client";

import Link from "next/link";
import { Card } from "@hostel/ui";
import { useTheme } from "@hostel/ui";
import { PwaSettingsCard } from "@hostel/pwa";
import { StorageCard } from "@hostel/pwa";
import { Clock, DatabaseBackup, Moon, Monitor, RefreshCw, Sun, Wallet } from "lucide-react";

const THEMES = [
  { value: "light", label: "Light", icon: Sun },
  { value: "dark", label: "Dark", icon: Moon },
  { value: "system", label: "System", icon: Monitor },
] as const;

export function PreferencesSection() {
  const { theme, setTheme } = useTheme();

  return (
    <div className="space-y-4">
      <Card>
        <div className="mb-1 text-base font-semibold text-[var(--foreground)]">Appearance</div>
        <p className="mb-4 text-sm text-[var(--muted)]">Choose how the dashboard looks on this device.</p>
        <div className="grid gap-3 sm:grid-cols-3">
          {THEMES.map(({ value, label, icon: Icon }) => {
            const active = theme === value;
            return (
              <button
                key={value}
                type="button"
                onClick={() => setTheme(value)}
                aria-pressed={active}
                className={`flex items-center gap-3 rounded-xl border p-3 text-left transition ${
                  active
                    ? "border-[var(--accent)] bg-[var(--accent-soft)]"
                    : "border-[var(--border)] bg-[var(--card)] hover:border-[var(--border-hover)] hover:bg-[var(--background-secondary)]"
                }`}
              >
                <span
                  className={`grid h-9 w-9 place-items-center rounded-lg ${
                    active ? "bg-[var(--accent)] text-white" : "bg-[var(--background-secondary)] text-[var(--muted)]"
                  }`}
                >
                  <Icon className="h-4 w-4" />
                </span>
                <span className="text-sm font-medium text-[var(--foreground)]">{label}</span>
              </button>
            );
          })}
        </div>
      </Card>

      <Card>
        <div className="mb-4 text-base font-semibold text-[var(--foreground)]">Regional</div>
        <div className="grid gap-3 sm:grid-cols-2">
          <Info icon={<Clock className="h-4 w-4" />} label="Timezone" value="Asia/Kathmandu" />
          <Info icon={<Wallet className="h-4 w-4" />} label="Currency" value="NPR (Rs.)" />
        </div>
      </Card>

      <PwaSettingsCard />

      <StorageCard />

      <Card>
        <div className="mb-3 text-base font-semibold text-[var(--foreground)]">Data & sync</div>
        <div className="flex flex-wrap gap-3">
          <Link
            href="/backup"
            className="inline-flex items-center gap-2 rounded-xl border border-[var(--border)] bg-[var(--card)] px-3 py-2 text-sm font-medium text-[var(--foreground)] transition hover:border-[var(--border-hover)] hover:bg-[var(--background-secondary)]"
          >
            <DatabaseBackup className="h-4 w-4 text-[var(--muted)]" />
            Backup settings
          </Link>
          <Link
            href="/sync"
            className="inline-flex items-center gap-2 rounded-xl border border-[var(--border)] bg-[var(--card)] px-3 py-2 text-sm font-medium text-[var(--foreground)] transition hover:border-[var(--border-hover)] hover:bg-[var(--background-secondary)]"
          >
            <RefreshCw className="h-4 w-4 text-[var(--muted)]" />
            Offline & sync
          </Link>
        </div>
      </Card>
    </div>
  );
}

function Info({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="flex items-center gap-3 rounded-xl bg-[var(--background-secondary)] px-4 py-3">
      <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-[var(--card)] text-[var(--muted)]">
        {icon}
      </span>
      <div>
        <div className="text-[11px] font-semibold uppercase tracking-wider text-[var(--muted)]">{label}</div>
        <div className="text-sm font-medium text-[var(--foreground)]">{value}</div>
      </div>
    </div>
  );
}
