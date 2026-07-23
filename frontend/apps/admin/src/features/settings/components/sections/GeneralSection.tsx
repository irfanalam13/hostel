"use client";

import { useEffect, useState } from "react";
import { Building2, Globe, Clock, Coins } from "lucide-react";
import Link from "next/link";
import { authStore } from "@hostel/auth";
import { tenantsApi } from "@/features/tenants/api/tenants.api";
import type { Hostel } from "@/features/tenants/types/tenants.types";
import { HostelSettingsCard } from "@/features/tenants/components/HostelSettingsCard";
import { Skeleton } from "@hostel/ui";
import { SectionHeader, SettingsPanel, DetailRow } from "../primitives";

/**
 * General workspace settings. Surfaces the active hostel's identity and regional
 * defaults (carried over from the legacy /settings page) and reuses the existing
 * admission-settings editor so nothing is duplicated.
 */
export function GeneralSection() {
  const [hostel, setHostel] = useState<Hostel | null>(null);
  const [loading, setLoading] = useState(true);
  const code = authStore.getHostelCode();

  useEffect(() => {
    tenantsApi.hostels
      .list()
      .then((hostels) => {
        setHostel(hostels.find((h) => h.code === code) || hostels[0] || null);
      })
      .catch(() => {
        /* non-staff can't list hostels — fall back to the code from the session */
      })
      .finally(() => setLoading(false));
  }, [code]);

  return (
    <div className="space-y-5">
      <SectionHeader
        icon={Building2}
        title="General"
        description="Your hostel's identity, contact details and admission defaults."
        status="ready"
      />

      <SettingsPanel title="Hostel identity" description="Basic details for the active hostel." icon={Building2}>
        {loading ? (
          <div className="space-y-3">
            <Skeleton className="h-4 w-56" />
            <Skeleton className="h-4 w-40" />
          </div>
        ) : (
          <div className="divide-y divide-[var(--border)]">
            <DetailRow label="Hostel name">{hostel?.name ?? "—"}</DetailRow>
            <DetailRow label="Hostel code">
              <span className="font-mono">{hostel?.code ?? code ?? "—"}</span>
            </DetailRow>
            <DetailRow label="Phone">{hostel?.phone || "—"}</DetailRow>
            <DetailRow label="Address">{hostel?.address || "—"}</DetailRow>
            <DetailRow label="Current plan">{hostel?.plan_name || "Free"}</DetailRow>
            <DetailRow label="Status">
              <span style={{ color: hostel?.is_active === false ? "var(--warning)" : "var(--success)" }}>
                {hostel?.is_active === false ? "Inactive" : "Active"}
              </span>
            </DetailRow>
          </div>
        )}
      </SettingsPanel>

      <SettingsPanel
        title="Regional defaults"
        description="Applied across the workspace."
        icon={Globe}
        footer={
          <p className="text-xs text-[var(--muted)]">
            Configurable timezone, currency and formats are coming in{" "}
            <Link href="/settings/localization" className="font-medium text-[var(--accent)] hover:underline">
              Localization
            </Link>
            .
          </p>
        }
      >
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="flex items-center gap-3 rounded-xl bg-[var(--background-secondary)] px-4 py-3">
            <Clock className="h-4 w-4 text-[var(--accent)]" />
            <div>
              <div className="text-xs text-[var(--muted)]">Timezone</div>
              <div className="text-sm font-medium text-[var(--foreground)]">Asia/Kathmandu</div>
            </div>
          </div>
          <div className="flex items-center gap-3 rounded-xl bg-[var(--background-secondary)] px-4 py-3">
            <Coins className="h-4 w-4 text-[var(--accent)]" />
            <div>
              <div className="text-xs text-[var(--muted)]">Currency</div>
              <div className="text-sm font-medium text-[var(--foreground)]">NPR (Rs.)</div>
            </div>
          </div>
        </div>
      </SettingsPanel>

      {/* Existing editable admission settings — reused, not duplicated. */}
      <HostelSettingsCard />
    </div>
  );
}
