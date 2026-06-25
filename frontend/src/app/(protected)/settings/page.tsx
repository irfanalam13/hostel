"use client";

import Link from "next/link";
import { API_BASE } from "@/shared/api/apiClient";
import { authStore } from "@/shared/auth/auth.store";
import { Topbar } from "@/shared/ui/Topbar";

export default function SettingsPage() {
  return (
    <div>
      <Topbar title="Settings" />

      <div className="rounded-2xl border bg-white p-4 space-y-3 text-sm">
        <div>
          <span className="text-gray-500">API Base:</span>{" "}
          <span className="font-mono">{API_BASE}</span>
        </div>
        <div>
          <span className="text-gray-500">Hostel Code:</span>{" "}
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
        <Link className="text-blue-600 hover:underline" href="/backup">
          Backup settings
        </Link>
      </div>
    </div>
  );
}
