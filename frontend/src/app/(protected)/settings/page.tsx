"use client";

import Link from "next/link";
import { API_BASE } from "@/shared/api/apiClient";
import { authStore } from "@/shared/auth/auth.store";
import { Topbar } from "@/shared/ui/Topbar";
import { PwaSettingsCard } from "@/shared/pwa/components/PwaSettingsCard";
import { StorageCard } from "@/shared/pwa/components/StorageCard";
import { HostelSettingsCard } from "@/features/tenants/components/HostelSettingsCard";

export default function SettingsPage() {
  return (
    <div className="space-y-4">
      <Topbar title="Settings" />

      <div className="rounded-2xl border bg-white p-4 space-y-3 text-sm">
        <div>
          <span className="text-gray-500">API Base:</span>{" "}
          <span className="font-mono">{API_BASE}</span>
        </div>
        <div>
          <span className="text-gray-500">Hostel ID:</span>{" "}
          <span className="font-mono">{authStore.getHostelCode() || "-"}</span>
        </div>
        <div>
          <span className="text-gray-500">Timezone:</span>{" "}
          <span>Asia/Kathmandu</span>
        </div>
        <div>
          <span className="text-gray-500">Currency:</span>{" "}
          <span>NPR (Rs.)</span>
        </div>
        <div className="flex gap-4">
          <Link className="text-blue-600 hover:underline" href="/backup">
            Backup settings
          </Link>
          <Link className="text-blue-600 hover:underline" href="/sync">
            Offline &amp; sync
          </Link>
        </div>
      </div>

      <HostelSettingsCard />

      <PwaSettingsCard />

      <StorageCard />
    </div>
  );
}
