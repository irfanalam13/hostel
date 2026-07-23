"use client";

import React, { useEffect, useState } from "react";
import { tenantsApi } from "@/features/tenants/api/tenants.api";
import type { Hostel, HostelCreateInput } from "@/features/tenants/types/tenants.types";
import { HostelForm } from "@/features/tenants/components/HostelForm";
import { HostelList } from "@/features/tenants/components/HostelList";

export default function HostelsPage() {
  const [hostels, setHostels] = useState<Hostel[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    setError(null);
    try {
      const data = await tenantsApi.hostels.list();
      setHostels(data);
    } catch (e: any) {
      setError(e.message);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function createHostel(payload: HostelCreateInput) {
    await tenantsApi.hostels.create(payload);
    await refresh();
  }

  async function deleteHostel(id: string) {
    await tenantsApi.hostels.remove(id);
    await refresh();
  }

  async function toggleActive(h: Hostel) {
    await tenantsApi.hostels.update(h.id, { is_active: !h.is_active });
    await refresh();
  }

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-xl font-semibold">Hostels</h1>
      {error && <div className="text-sm text-red-600">{error}</div>}

      <HostelForm onSubmit={createHostel} submitLabel="Create hostel" />

      <HostelList hostels={hostels} onDelete={deleteHostel} onQuickToggleActive={toggleActive} />
    </div>
  );
}
