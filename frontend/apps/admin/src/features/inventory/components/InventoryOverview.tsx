"use client";

import React from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ErrorState, StatCardsSkeleton } from "@hostel/ui";
import { useApi } from "@hostel/hooks";

import { inventoryApi } from "../api/inventory.api";
import { StatCard, StatusBadge, cardClass, formatMoney, formatQty } from "./primitives";

const PIE_COLORS = [
  "var(--accent)",
  "var(--success)",
  "var(--warning)",
  "var(--info)",
  "var(--error)",
  "#8b5cf6",
  "#ec4899",
  "#14b8a6",
  "#f97316",
  "#64748b",
];

type TooltipRenderProps = {
  active?: boolean;
  label?: string | number;
  payload?: { name?: string; dataKey?: string | number; value?: number | string }[];
};

function ChartTooltip({ active, payload, label }: TooltipRenderProps) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--card-elevated)] px-3 py-2 text-xs shadow-[var(--shadow-lg)]">
      {label ? <div className="mb-1 font-semibold text-[var(--foreground)]">{label}</div> : null}
      {payload.map((item) => (
        <div key={item.dataKey ?? item.name} className="text-[var(--foreground-secondary)]">
          {(item.name ?? item.dataKey) as string}: {formatQty(Number(item.value || 0))}
        </div>
      ))}
    </div>
  );
}

export function InventoryOverview() {
  const { data, loading, error, refetch } = useApi(() => inventoryApi.dashboard.summary());

  if (loading) {
    return (
      <div className="space-y-4">
        <StatCardsSkeleton count={4} />
        <StatCardsSkeleton count={4} />
      </div>
    );
  }

  if (error || !data) {
    return <ErrorState description={error || "Couldn't load the inventory dashboard."} onRetry={refetch} />;
  }

  const t = data.totals;

  // Aggregate movement trend by month (in vs out).
  const byMonth = new Map<string, { month: string; In: number; Out: number }>();
  for (const p of data.movement_trend) {
    if (!p.month) continue;
    const row = byMonth.get(p.month) ?? { month: p.month, In: 0, Out: 0 };
    if (p.direction === "in") row.In += Number(p.quantity);
    else row.Out += Number(p.quantity);
    byMonth.set(p.month, row);
  }
  const movements = Array.from(byMonth.values());
  const categories = data.by_category.map((c) => ({ name: c.category, value: c.count }));

  return (
    <div className="space-y-5">
      {/* Primary KPIs */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Inventory Value" value={formatMoney(t.inventory_value)} tone="accent" />
        <StatCard label="Total Items" value={t.total_items} hint={`${t.active_items} active`} />
        <StatCard label="Total Assets" value={t.total_assets} hint={`${t.active_assets} in use`} />
        <StatCard label="Vendors" value={t.total_vendors} />
        <StatCard label="Low Stock" value={t.low_stock} tone="warning" />
        <StatCard label="Out of Stock" value={t.out_of_stock} tone="error" />
        <StatCard label="Overstock" value={t.overstock} />
        <StatCard label="Open Purchase Orders" value={t.open_purchase_orders} tone="accent" />
        <StatCard label="Pending Deliveries" value={t.pending_deliveries} tone="warning" />
        <StatCard label="In Maintenance" value={t.maintenance_assets} tone="warning" />
        <StatCard label="Damaged Assets" value={t.damaged_assets} tone="error" />
        <StatCard label="Retired / Disposed" value={t.inactive_assets} />
      </div>

      {/* Movement trend + category distribution */}
      <div className="grid gap-5 lg:grid-cols-3">
        <div className={`${cardClass} lg:col-span-2`}>
          <h3 className="mb-1 text-sm font-semibold text-[var(--foreground-secondary)]">Stock Movement</h3>
          <p className="mb-4 text-[11px] text-[var(--muted)]">Units in vs out by month</p>
          <div className="h-64 w-full">
            {movements.length === 0 ? (
              <div className="grid h-full place-items-center text-sm text-[var(--muted)]">
                No stock movement yet.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={movements} margin={{ top: 5, right: 5, left: -10, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" />
                  <XAxis dataKey="month" tickLine={false} tick={{ fontSize: 11, fill: "var(--muted)" }} />
                  <YAxis tickLine={false} tick={{ fontSize: 11, fill: "var(--muted)" }} />
                  <Tooltip content={<ChartTooltip />} cursor={{ fill: "var(--background-secondary)" }} />
                  <Bar dataKey="In" fill="var(--success)" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="Out" fill="var(--error)" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        <div className={cardClass}>
          <h3 className="mb-1 text-sm font-semibold text-[var(--foreground-secondary)]">Items by Category</h3>
          <p className="mb-4 text-[11px] text-[var(--muted)]">Distribution of catalog items</p>
          <div className="h-52 w-full">
            {categories.length === 0 ? (
              <div className="grid h-full place-items-center text-sm text-[var(--muted)]">
                No items catalogued.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={categories} cx="50%" cy="50%" innerRadius={45} outerRadius={72} paddingAngle={3} dataKey="value">
                    {categories.map((entry, i) => (
                      <Cell key={entry.name} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip content={<ChartTooltip />} />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>
          <div className="mt-2 space-y-1.5">
            {categories.map((c, i) => (
              <div key={c.name} className="flex items-center justify-between text-xs">
                <span className="flex items-center gap-1.5 text-[var(--foreground-secondary)]">
                  <span className="h-2 w-2 rounded-full" style={{ backgroundColor: PIE_COLORS[i % PIE_COLORS.length] }} />
                  {c.name}
                </span>
                <span className="font-semibold text-[var(--foreground)]">{c.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Recent movements */}
      <div className={cardClass}>
        <h3 className="mb-3 text-sm font-semibold text-[var(--foreground-secondary)]">Recent Stock Movements</h3>
        {data.recent_movements.length === 0 ? (
          <p className="py-6 text-center text-sm text-[var(--muted)]">No movements yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-[var(--border)] text-[var(--muted)]">
                  <th className="py-2 pr-3 font-medium">Ref</th>
                  <th className="py-2 pr-3 font-medium">Item</th>
                  <th className="py-2 pr-3 font-medium">Type</th>
                  <th className="py-2 pr-3 font-medium text-right">Qty</th>
                  <th className="py-2 font-medium text-right">When</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border)]">
                {data.recent_movements.map((m) => (
                  <tr key={m.id}>
                    <td className="py-2.5 pr-3 font-mono text-xs text-[var(--foreground-secondary)]">{m.reference}</td>
                    <td className="py-2.5 pr-3 text-[var(--foreground)]">{m.item_name}</td>
                    <td className="py-2.5 pr-3"><StatusBadge status={m.direction} label={m.movement_type.replace(/_/g, " ")} /></td>
                    <td className="py-2.5 pr-3 text-right font-semibold text-[var(--foreground)]">{formatQty(m.quantity)}</td>
                    <td className="py-2.5 text-right text-[var(--muted)]">{new Date(m.occurred_at).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
