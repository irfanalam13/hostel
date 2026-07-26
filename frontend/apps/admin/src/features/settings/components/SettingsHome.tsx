"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Building2,
  CreditCard,
  UserCircle,
  ShieldCheck,
  ArrowRight,
  Sparkles,
  Palette,
  DatabaseBackup,
  Bell,
  Users,
  Server,
  Wifi,
  WifiOff,
} from "lucide-react";
import { useAuth } from "@hostel/auth";
import { authStore } from "@hostel/auth";
import { tenantsApi } from "@/features/tenants/api/tenants.api";
import type { Hostel } from "@/features/tenants/types/tenants.types";
import { ActivitySection } from "@/features/account/components/ActivitySection";
import { profileCompletion, roleLabel, formatDate } from "@/features/account/lib";
import { Skeleton } from "@hostel/ui";
import { StatTile, SettingsPanel, DetailRow } from "./primitives";

const QUICK_ACTIONS: {
  href: string;
  label: string;
  hint: string;
  icon: React.ComponentType<{ className?: string }>;
}[] = [
  { href: "/settings/general", label: "General", hint: "Hostel details & defaults", icon: Building2 },
  { href: "/settings/appearance", label: "Appearance", hint: "Theme & display", icon: Palette },
  { href: "/settings/backups", label: "Backups", hint: "Backup & restore", icon: DatabaseBackup },
  { href: "/settings/notifications", label: "Notifications", hint: "Alerts & digests", icon: Bell },
  { href: "/settings/users", label: "Users & staff", hint: "Manage accounts", icon: Users },
  { href: "/settings/system", label: "System", hint: "Health & environment", icon: Server },
];

export function SettingsHome() {
  const { user } = useAuth();
  const [hostel, setHostel] = useState<Hostel | null>(null);
  const [loading, setLoading] = useState(true);
  const [online, setOnline] = useState(true);
  const code = authStore.getHostelCode();

  useEffect(() => {
    setOnline(navigator.onLine);
    const on = () => setOnline(true);
    const off = () => setOnline(false);
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    tenantsApi.hostels
      .list()
      .then((hostels) => setHostel(hostels.find((h) => h.code === code) || hostels[0] || null))
      .catch(() => {
        /* non-staff can't list hostels — dashboard degrades gracefully */
      })
      .finally(() => setLoading(false));
    return () => {
      window.removeEventListener("online", on);
      window.removeEventListener("offline", off);
    };
  }, [code]);

  const completion = profileCompletion(user);

  return (
    <div className="space-y-5">
      {/* Hero */}
      <div className="overflow-hidden rounded-[20px] border border-[var(--border)] bg-gradient-to-br from-[color-mix(in_srgb,var(--accent)_12%,var(--card))] to-[var(--card)] p-6 shadow-[var(--shadow-sm)]">
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-[var(--accent)]">
          <Sparkles className="h-3.5 w-3.5" />
          Workspace settings
        </div>
        <h1 className="mt-1 text-2xl font-semibold text-[var(--foreground)]">
          {hostel?.name ? hostel.name : "Your hostel"}
        </h1>
        <p className="mt-1 max-w-2xl text-sm text-[var(--muted)]">
          Manage your organization, security, billing and system preferences from one place. Use the search or the menu
          to jump to any setting.
        </p>
      </div>

      {/* Stat tiles */}
      {loading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="rounded-[18px] border border-[var(--border)] bg-[var(--card)] p-4">
              <Skeleton className="mb-3 h-3 w-20" />
              <Skeleton className="h-7 w-24" />
            </div>
          ))}
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatTile
            label="Current plan"
            value={hostel?.plan_name || "Free"}
            hint={
              hostel?.subscription_active_until
                ? `Renews ${formatDate(hostel.subscription_active_until)}`
                : "Starter tier"
            }
            icon={CreditCard}
          />
          <StatTile
            label="Workspace"
            value={hostel?.is_active === false ? "Inactive" : "Active"}
            hint={hostel?.code ? `Code ${hostel.code}` : code ? `Code ${code}` : "—"}
            icon={Building2}
            tone={hostel?.is_active === false ? "var(--warning)" : "var(--success)"}
          />
          <StatTile
            label="Your role"
            value={roleLabel(user?.role)}
            hint={user?.username ? `@${user.username}` : undefined}
            icon={ShieldCheck}
            tone="var(--info)"
          />
          <StatTile
            label="Profile completion"
            value={`${completion.percent}%`}
            hint={completion.percent < 100 ? "Finish your profile" : "All set"}
            icon={UserCircle}
            tone={completion.percent < 100 ? "var(--warning)" : "var(--success)"}
          />
        </div>
      )}

      <div className="grid gap-5 lg:grid-cols-3">
        {/* Quick actions */}
        <SettingsPanel title="Quick actions" description="Jump straight to a common setting." className="lg:col-span-2">
          <div className="grid gap-3 sm:grid-cols-2">
            {QUICK_ACTIONS.map((a) => {
              const Icon = a.icon;
              return (
                <Link
                  key={a.href}
                  href={a.href}
                  className="group flex items-center gap-3 rounded-xl border border-[var(--border)] bg-[var(--card)] px-4 py-3 transition hover:border-[var(--border-hover)] hover:bg-[var(--background-secondary)]"
                >
                  <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-[color-mix(in_srgb,var(--accent)_12%,transparent)] text-[var(--accent)]">
                    <Icon className="h-4 w-4" />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block text-sm font-medium text-[var(--foreground)]">{a.label}</span>
                    <span className="block truncate text-xs text-[var(--muted)]">{a.hint}</span>
                  </span>
                  <ArrowRight className="h-4 w-4 shrink-0 text-[var(--muted)] transition group-hover:translate-x-0.5 group-hover:text-[var(--accent)]" />
                </Link>
              );
            })}
          </div>
        </SettingsPanel>

        {/* System health */}
        <SettingsPanel title="System health" icon={Server}>
          <div className="divide-y divide-[var(--border)]">
            <DetailRow label="Connectivity">
              <span
                className="inline-flex items-center gap-1.5"
                style={{ color: online ? "var(--success)" : "var(--warning)" }}
              >
                {online ? <Wifi className="h-4 w-4" /> : <WifiOff className="h-4 w-4" />}
                {online ? "Online" : "Offline"}
              </span>
            </DetailRow>
            <DetailRow label="Profile">
              {completion.percent < 100 ? (
                <Link href="/profile" className="text-[var(--accent)] hover:underline">
                  {completion.percent}% — complete it
                </Link>
              ) : (
                <span style={{ color: "var(--success)" }}>Complete</span>
              )}
            </DetailRow>
            <DetailRow label="Account">
              <Link href="/profile" className="text-[var(--accent)] hover:underline">
                Personal settings
              </Link>
            </DetailRow>
          </div>
        </SettingsPanel>
      </div>

      {/* Recent activity — reuses the account audit timeline */}
      <ActivitySection />
    </div>
  );
}
