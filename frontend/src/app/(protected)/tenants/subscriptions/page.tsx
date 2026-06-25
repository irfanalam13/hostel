"use client";

import React, { useEffect, useMemo, useState } from "react";
import { tenantsApi } from "@/features/tenants/api/tenants.api";
import type {
  Hostel,
  Plan,
  Subscription,
  SubscriptionCreateInput,
} from "@/features/tenants/types/tenants.types";
import { SubscriptionForm } from "@/features/tenants/components/SubscriptionForm";
import { SubscriptionList } from "@/features/tenants/components/SubscriptionList";

function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;

  // Try common keys (choose one that matches your backend login later)
  return (
    localStorage.getItem("access") ||
    localStorage.getItem("access_token") ||
    localStorage.getItem("token") ||
    null
  );
}

export default function TenantsSubscriptionsPage() {
  const token = useMemo(() => getAccessToken(), []);

  const [hostels, setHostels] = useState<Hostel[]>([]);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [subs, setSubs] = useState<Subscription[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function refreshAll() {
    setError(null);
    try {
      const [h, p] = await Promise.all([
        tenantsApi.hostels.list(),
        tenantsApi.plans.list(),
      ]);
      setHostels(h);
      setPlans(p);

      // Auth required:
      const s = await tenantsApi.subscriptions.list(token);
      setSubs(s);
    } catch (e: any) {
      setError(e.message);
    }
  }

  useEffect(() => {
    refreshAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function createSub(payload: SubscriptionCreateInput) {
    await tenantsApi.subscriptions.create(payload, token);
    await refreshAll();
  }

  async function deleteSub(id: string) {
    await tenantsApi.subscriptions.remove(id, token);
    await refreshAll();
  }

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-xl font-semibold">Subscriptions</h1>

      {!token && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
          No token found in localStorage. Subscriptions API requires authentication.
          <div className="mt-1 text-xs">
            Expected localStorage key: <b>access</b> or <b>access_token</b> or <b>token</b>.
          </div>
        </div>
      )}

      {error && <div className="text-sm text-red-600">{error}</div>}

      <SubscriptionForm hostels={hostels} plans={plans} onSubmit={createSub} />
      <SubscriptionList subs={subs} onDelete={deleteSub} />
    </div>
  );
}
