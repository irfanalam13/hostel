"use client";

import React from "react";
import type { OwnerDashboardResponse } from "../types";

function formatMoney(n: number) {
  // keep simple; you can replace with NPR formatting later
  return Number(n || 0).toLocaleString();
}

function StatCard({
  title,
  value,
  subtitle,
}: {
  title: string;
  value: string;
  subtitle?: string;
}) {
  return (
    <div className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm">
      <div className="text-sm text-zinc-500">{title}</div>
      <div className="mt-1 text-2xl font-semibold text-zinc-900">{value}</div>
      {subtitle ? (
        <div className="mt-1 text-xs text-zinc-500">{subtitle}</div>
      ) : null}
    </div>
  );
}

export function OwnerDashboardCards({ data }: { data: OwnerDashboardResponse }) {
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      <StatCard
        title="Active Residents"
        value={String(data.total_residents || 0)}
        subtitle="Currently active students"
      />

      <StatCard
        title="Today Collection"
        value={`Rs. ${formatMoney(data.today_collection)}`}
        subtitle="Collected today"
      />

      <StatCard
        title="This Month Collection"
        value={`Rs. ${formatMoney(data.month_collection)}`}
        subtitle={`Month: ${data.this_month}`}
      />

      <StatCard
        title="Due Amount (This Month)"
        value={`Rs. ${formatMoney(data.total_due_this_month)}`}
        subtitle={`Students due: ${data.due_students_this_month}`}
      />

      <StatCard
        title="Total Beds"
        value={String(data.beds.total)}
        subtitle="All beds in hostel"
      />

      <StatCard
        title="Occupied Beds"
        value={String(data.beds.occupied)}
        subtitle="Currently occupied"
      />

      <StatCard
        title="Available Beds"
        value={String(data.beds.available)}
        subtitle={`${data.beds.occupancy_percent || 0}% occupancy`}
      />

      <StatCard
        title="Pending Complaints"
        value={String(data.pending_complaints || 0)}
        subtitle="Open or in progress"
      />

      <StatCard
        title="Admissions Queue"
        value={String(data.pending_admissions || 0)}
        subtitle="Pending approval"
      />

      <StatCard
        title="Gate & Leave"
        value={String(data.today_entries || 0)}
        subtitle={`${data.pending_leave_requests || 0} leave request(s) pending`}
      />
    </div>
  );
}
