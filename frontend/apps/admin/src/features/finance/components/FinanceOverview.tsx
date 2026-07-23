"use client";

import React from "react";
import Link from "next/link";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ErrorState, StatCardsSkeleton } from "@hostel/ui";
import { useApi } from "@hostel/hooks";

import { financeApi } from "../api/finance.api";
import { StatCard, StatusBadge, formatMoney } from "./primitives";

const cardClass =
  "rounded-[20px] border border-[var(--border)] bg-[var(--card)] p-5 shadow-[var(--shadow-sm)]";

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

const methodLabel = (m: string) => m.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

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
          {(item.name ?? item.dataKey) as string}: {formatMoney(Number(item.value || 0))}
        </div>
      ))}
    </div>
  );
}

export function FinanceOverview() {
  const { data, loading, error, refetch } = useApi(() => financeApi.dashboard.summary());

  if (loading) {
    return (
      <div className="space-y-4">
        <StatCardsSkeleton count={4} />
        <StatCardsSkeleton count={4} />
      </div>
    );
  }

  if (error || !data) {
    return <ErrorState description={error || "Couldn't load the finance dashboard."} onRetry={refetch} />;
  }

  const t = data.totals;
  const cashFlow = data.cash_flow.map((p) => ({
    month: p.month,
    In: Number(p.in),
    Out: Number(p.out),
  }));
  const methods = data.payment_methods.map((m) => ({
    name: methodLabel(m.method),
    value: Number(m.total),
    count: m.count,
  }));

  return (
    <div className="space-y-5">
      {/* Primary money KPIs */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Total Revenue" value={formatMoney(t.total_revenue)} tone="success" />
        <StatCard label="Total Expenses" value={formatMoney(t.total_expenses)} tone="error" />
        <StatCard label="Net Profit" value={formatMoney(t.net_profit)} tone="accent" />
        <StatCard label="Outstanding Due" value={formatMoney(t.outstanding_due)} tone="warning" />
        <StatCard label="Today's Collection" value={formatMoney(t.todays_collection)} />
        <StatCard label="Monthly Collection" value={formatMoney(t.monthly_collection)} />
        <StatCard label="Annual Revenue" value={formatMoney(t.annual_revenue)} />
        <StatCard label="Refunds" value={formatMoney(t.refund_total)} />
        <StatCard label="Discounts" value={formatMoney(t.discount_total)} />
        <StatCard label="Scholarships" value={formatMoney(t.scholarship_total)} />
        <StatCard label="Pending Payments" value={t.pending_payments} tone="warning" />
        <StatCard label="Overdue Invoices" value={t.overdue_invoices} tone="error" />
      </div>

      {/* Cash-flow + payment methods */}
      <div className="grid gap-5 lg:grid-cols-3">
        <div className={`${cardClass} lg:col-span-2`}>
          <h3 className="mb-1 text-sm font-semibold text-[var(--foreground-secondary)]">Cash Flow</h3>
          <p className="mb-4 text-[11px] text-[var(--muted)]">Money in vs money out by month</p>
          <div className="h-64 w-full">
            {cashFlow.length === 0 ? (
              <div className="grid h-full place-items-center text-sm text-[var(--muted)]">
                No cash-flow data yet.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={cashFlow} margin={{ top: 5, right: 5, left: -10, bottom: 5 }}>
                  <defs>
                    <linearGradient id="financeIn" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="var(--success)" stopOpacity={0.28} />
                      <stop offset="95%" stopColor="var(--success)" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="financeOut" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="var(--error)" stopOpacity={0.28} />
                      <stop offset="95%" stopColor="var(--error)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" />
                  <XAxis dataKey="month" tickLine={false} tick={{ fontSize: 11, fill: "var(--muted)" }} />
                  <YAxis tickLine={false} tick={{ fontSize: 11, fill: "var(--muted)" }} />
                  <Tooltip content={<ChartTooltip />} />
                  <Legend iconType="circle" wrapperStyle={{ fontSize: "11px", color: "var(--muted)" }} />
                  <Area type="monotone" dataKey="In" stroke="var(--success)" strokeWidth={3} fillOpacity={1} fill="url(#financeIn)" />
                  <Area type="monotone" dataKey="Out" stroke="var(--error)" strokeWidth={3} fillOpacity={1} fill="url(#financeOut)" />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        <div className={cardClass}>
          <h3 className="mb-1 text-sm font-semibold text-[var(--foreground-secondary)]">Payment Methods</h3>
          <p className="mb-4 text-[11px] text-[var(--muted)]">Collected by method</p>
          <div className="h-52 w-full">
            {methods.length === 0 ? (
              <div className="grid h-full place-items-center text-sm text-[var(--muted)]">
                No payments recorded.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={methods} cx="50%" cy="50%" innerRadius={45} outerRadius={72} paddingAngle={3} dataKey="value">
                    {methods.map((entry, i) => (
                      <Cell key={entry.name} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip content={<ChartTooltip />} />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>
          <div className="mt-2 space-y-1.5">
            {methods.map((m, i) => (
              <div key={m.name} className="flex items-center justify-between text-xs">
                <span className="flex items-center gap-1.5 text-[var(--foreground-secondary)]">
                  <span className="h-2 w-2 rounded-full" style={{ backgroundColor: PIE_COLORS[i % PIE_COLORS.length] }} />
                  {m.name}
                </span>
                <span className="font-semibold text-[var(--foreground)]">{formatMoney(m.value)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Upcoming dues + recent transactions */}
      <div className="grid gap-5 lg:grid-cols-2">
        <div className={cardClass}>
          <h3 className="mb-3 text-sm font-semibold text-[var(--foreground-secondary)]">Upcoming Dues</h3>
          {data.upcoming_dues.length === 0 ? (
            <p className="py-6 text-center text-sm text-[var(--muted)]">No upcoming dues.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-[var(--border)] text-[var(--muted)]">
                    <th className="py-2 pr-3 font-medium">Invoice</th>
                    <th className="py-2 pr-3 font-medium">Resident</th>
                    <th className="py-2 pr-3 font-medium">Due</th>
                    <th className="py-2 pr-3 font-medium text-right">Balance</th>
                    <th className="py-2 font-medium text-right">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border)]">
                  {data.upcoming_dues.map((d) => (
                    <tr key={d.id}>
                      <td className="py-2.5 pr-3">
                        <Link href={`/finance/invoices/${d.id}`} className="font-medium text-[var(--foreground)] hover:text-[var(--accent)]">
                          {d.number}
                        </Link>
                      </td>
                      <td className="py-2.5 pr-3 text-[var(--foreground-secondary)]">{d.resident_name}</td>
                      <td className="py-2.5 pr-3 text-[var(--foreground-secondary)]">{d.due_date}</td>
                      <td className="py-2.5 pr-3 text-right font-semibold text-[var(--foreground)]">{formatMoney(d.balance)}</td>
                      <td className="py-2.5 text-right"><StatusBadge status={d.status} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className={cardClass}>
          <h3 className="mb-3 text-sm font-semibold text-[var(--foreground-secondary)]">Recent Transactions</h3>
          {data.recent_transactions.length === 0 ? (
            <p className="py-6 text-center text-sm text-[var(--muted)]">No transactions yet.</p>
          ) : (
            <div className="space-y-1.5">
              {data.recent_transactions.map((tx) => {
                const inbound = tx.direction === "in";
                const color = inbound ? "var(--success)" : "var(--error)";
                return (
                  <div
                    key={tx.id}
                    className="flex items-center justify-between rounded-xl border border-[var(--border)] bg-[var(--background-secondary)] px-3 py-2"
                  >
                    <div className="min-w-0">
                      <div className="truncate text-sm font-medium text-[var(--foreground)]">
                        {tx.memo || tx.category || methodLabel(tx.method)}
                      </div>
                      <div className="text-[11px] text-[var(--muted)]">
                        {tx.resident_name ? `${tx.resident_name} · ` : ""}
                        {new Date(tx.occurred_at).toLocaleDateString()} · {methodLabel(tx.method)}
                      </div>
                    </div>
                    <div className="shrink-0 text-sm font-bold" style={{ color }}>
                      {inbound ? "+" : "−"}
                      {formatMoney(tx.amount)}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
