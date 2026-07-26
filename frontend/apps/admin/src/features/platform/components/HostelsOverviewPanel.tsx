"use client";

import React, { useEffect, useState } from "react";
import { EmptyState, Table, useToast } from "@hostel/ui";
import { platformApi } from "../api/platform.api";
import type { HostelOverviewRow } from "../types/platform.types";
import { Badge } from "./primitives";

const STATUS_TONE: Record<string, string> = {
  active: "var(--success)",
  trial: "var(--info)",
  expired: "var(--warning)",
  suspended: "var(--error)",
  pending: "var(--muted)",
};

/** Every hostel's OWN business numbers in one place — students, occupancy,
 * revenue, dues. Super-admin only: the backend gates this on
 * IsPlatformAdmin (user.is_superuser), never on tenant OWNER/ADMIN grants, so
 * no cross-tenant business data can leak to a hostel owner. */
export function HostelsOverviewPanel() {
  const toast = useToast();
  const [rows, setRows] = useState<HostelOverviewRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    platformApi.hostelsOverview
      .list()
      .then(setRows)
      .catch((e) => toast.error((e as Error).message))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (loading) return <div className="text-sm text-[var(--muted)]">Loading hostels…</div>;

  const totals = rows.reduce(
    (acc, r) => ({
      students: acc.students + r.active_students,
      revenue: acc.revenue + Number(r.month_revenue || 0),
    }),
    { students: 0, revenue: 0 },
  );
  const tiles = [
    { label: "Hostels", value: rows.length, sub: "workspaces" },
    { label: "Active students", value: totals.students, sub: "across all hostels" },
    { label: "Revenue this month", value: `Rs. ${totals.revenue.toLocaleString()}`, sub: "all hostels combined" },
  ];

  return (
    <div className="space-y-5">
      <div className="grid gap-4 sm:grid-cols-3">
        {tiles.map((t) => (
          <div key={t.label} className="rounded-[20px] border border-[var(--border)] bg-[var(--card)] p-5">
            <div className="text-sm text-[var(--muted)]">{t.label}</div>
            <div className="mt-1 text-3xl font-semibold text-[var(--foreground)]">{t.value}</div>
            <div className="text-xs text-[var(--muted)]">{t.sub}</div>
          </div>
        ))}
      </div>

      {rows.length === 0 ? (
        <EmptyState title="No hostels yet" description="Workspaces appear here once created." />
      ) : (
        <Table>
          <thead>
            <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
              <th className="px-4 py-3 font-medium">Hostel</th>
              <th className="px-4 py-3 font-medium">Owner</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Plan</th>
              <th className="px-4 py-3 font-medium text-right">Students</th>
              <th className="px-4 py-3 font-medium text-right">Occupancy</th>
              <th className="px-4 py-3 font-medium text-right">This month</th>
              <th className="px-4 py-3 font-medium text-right">Dues</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} className="border-b border-[var(--border)] last:border-0">
                <td className="px-4 py-3">
                  <div className="font-medium text-[var(--foreground)]">{r.name}</div>
                  <div className="text-xs text-[var(--muted)]">{r.code}</div>
                </td>
                <td className="px-4 py-3 text-[var(--foreground-secondary)]">{r.owner_name || "—"}</td>
                <td className="px-4 py-3">
                  <Badge color={STATUS_TONE[r.status] || "var(--muted)"}>{r.status}</Badge>
                </td>
                <td className="px-4 py-3 text-[var(--foreground-secondary)]">{r.plan_name || "—"}</td>
                <td className="px-4 py-3 text-right text-[var(--foreground-secondary)]">{r.active_students}</td>
                <td className="px-4 py-3 text-right text-[var(--foreground-secondary)]">
                  {r.beds_occupied}/{r.beds_total}
                </td>
                <td className="px-4 py-3 text-right text-[var(--foreground-secondary)]">Rs. {r.month_revenue}</td>
                <td className="px-4 py-3 text-right text-[var(--foreground-secondary)]">
                  {r.due_count > 0 ? (
                    <span className="text-[var(--warning)]">
                      Rs. {r.month_due} ({r.due_count})
                    </span>
                  ) : (
                    "—"
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </div>
  );
}
