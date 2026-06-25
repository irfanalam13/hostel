"use client";

import { useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import { Card } from "@/shared/ui/Card";
import { Topbar } from "@/shared/ui/Topbar";
import { Button } from "@/shared/ui/Button";
import { StatCardsSkeleton } from "@/shared/ui/Skeleton";
import { ErrorState } from "@/shared/ui/ErrorState";
import { EmptyState } from "@/shared/ui/EmptyState";
import { useApi } from "@/shared/hooks/useApi";
import { loadState } from "@/features/hostels/store";
import { ymToday } from "@/shared/lib/dates";
import { occupancy, computeDues, sumPayments } from "@/shared/lib/finance";
import { getOwnerDashboard } from "@/features/dashboard/api";
import type { OwnerDashboardResponse } from "@/features/dashboard/types";

// Heavy, chart-style cards are code-split so the dashboard shell paints fast.
const OwnerDashboardCards = dynamic(
  () => import("@/features/dashboard/components/OwnerDashboardCards").then((m) => m.OwnerDashboardCards),
  { loading: () => <StatCardsSkeleton count={4} />, ssr: false }
);

export default function DashboardPage() {
  const [tick, setTick] = useState(0);
  const ym = ymToday();

  const { data, loading, error, refetch } = useApi<OwnerDashboardResponse>(
    () => getOwnerDashboard(),
    { deps: [] }
  );

  useEffect(() => {
    const onFocus = () => setTick((t) => t + 1);
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, []);

  const state = useMemo(() => loadState(), [tick]);

  const todayCollection = sumPayments(state.payments, ym, true);
  const monthCollection = sumPayments(state.payments, ym, false);

  const activeStudents = state.students.filter((s) => s.status === "active");
  const { totalDue, studentsDue } = computeDues(activeStudents, state.payments, ym);

  const occ = occupancy(state.students, state.rooms, state.beds);
  const totalBeds = occ.totalBeds || state.settings.totalBeds || 0;
  const occupied = occ.occupied;
  const available = Math.max(0, totalBeds - occupied);

  return (
    <div>
      <Topbar title="Dashboard" />
      <div className="mb-3 text-xs text-gray-500">{state.settings.hostelName}</div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <div className="mb-2 text-sm text-gray-500">Collections</div>
          <div className="flex justify-between">
            <div>
              <div className="text-xs text-gray-500">Today</div>
              <div className="text-2xl font-semibold">{todayCollection}</div>
            </div>
            <div>
              <div className="text-xs text-gray-500">This Month ({ym})</div>
              <div className="text-2xl font-semibold">{monthCollection}</div>
            </div>
          </div>
        </Card>

        <Card>
          <div className="mb-2 text-sm text-gray-500">Dues</div>
          <div className="text-xs text-gray-500">Total Due (this month)</div>
          <div className="text-2xl font-semibold">{totalDue}</div>
          <div className="mt-2 text-sm">
            Students due: <b>{studentsDue}</b>
          </div>
        </Card>

        <Card>
          <div className="mb-2 text-sm text-gray-500">Beds</div>
          <div className="text-xs text-gray-500">Total</div>
          <div className="text-2xl font-semibold">{totalBeds}</div>
          <div className="mt-2 text-sm text-gray-700">
            Occupied: <b>{occupied}</b>
          </div>
          <div className="text-sm text-gray-700">
            Available: <b>{available}</b>
          </div>
        </Card>
      </div>

      <div className="p-4 md:p-6">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-zinc-900">Dashboard</h1>
            <p className="text-sm text-zinc-500">Owner overview (collection, dues, beds)</p>
          </div>
          <Button variant="ghost" onClick={refetch} loading={loading}>
            Refresh
          </Button>
        </div>

        {loading ? (
          <StatCardsSkeleton count={4} />
        ) : error ? (
          <ErrorState compact title="Couldn’t load dashboard" error={error} onRetry={refetch} />
        ) : data ? (
          <OwnerDashboardCards data={data} />
        ) : (
          <EmptyState title="No dashboard data" description="There’s nothing to show yet." />
        )}
      </div>
    </div>
  );
}
