"use client";

import React, { useMemo, useState } from "react";
import type { Hostel, Plan, SubscriptionCreateInput } from "../types/tenants.types";
import { Button } from "@hostel/ui";
import { Input } from "@hostel/ui";

export function SubscriptionForm({
  hostels,
  plans,
  onSubmit,
}: {
  hostels: Hostel[];
  plans: Plan[];
  onSubmit: (payload: SubscriptionCreateInput) => Promise<void>;
}) {
  const defaultHostel = hostels[0]?.id;
  const defaultPlan = plans[0]?.id;

  const today = useMemo(() => {
    const d = new Date();
    const yyyy = d.getFullYear();
    const mm = String(d.getMonth() + 1).padStart(2, "0");
    const dd = String(d.getDate()).padStart(2, "0");
    return `${yyyy}-${mm}-${dd}`;
  }, []);

  const [hostel, setHostel] = useState(defaultHostel ?? "");
  const [plan, setPlan] = useState(defaultPlan ?? "");
  const [startDate, setStartDate] = useState(today);
  const [endDate, setEndDate] = useState(today);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await onSubmit({
        hostel,
        plan,
        start_date: startDate,
        end_date: endDate,
        is_active: true,
      });
    } catch (err: any) {
      setError(err?.message || "Failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={submit} className="rounded-xl border border-zinc-200 bg-white p-4 space-y-3">
      <div className="font-semibold">Create subscription (needs auth)</div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <label className="text-sm text-zinc-700">
          Hostel
          <select
            className="mt-1 w-full rounded-xl border border-zinc-200 bg-white p-2"
            value={hostel}
            onChange={(e) => setHostel(e.target.value)}
          >
            {hostels.map((h) => (
              <option key={h.id} value={h.id}>{h.name} ({h.code})</option>
            ))}
          </select>
        </label>

        <label className="text-sm text-zinc-700">
          Plan
          <select
            className="mt-1 w-full rounded-xl border border-zinc-200 bg-white p-2"
            value={plan}
            onChange={(e) => setPlan(e.target.value)}
          >
            {plans.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </label>

        <label className="text-sm text-zinc-700">
          Start date
          <Input value={startDate} onChange={(e: any) => setStartDate(e.target.value)} />
        </label>

        <label className="text-sm text-zinc-700">
          End date
          <Input value={endDate} onChange={(e: any) => setEndDate(e.target.value)} />
        </label>
      </div>

      {error && <div className="text-sm text-red-600">{error}</div>}

      <Button type="submit" disabled={loading || !hostel || !plan}>
        {loading ? "Creating..." : "Create"}
      </Button>
    </form>
  );
}
