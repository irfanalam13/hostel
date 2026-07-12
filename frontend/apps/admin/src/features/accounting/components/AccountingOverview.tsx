"use client";

import React from "react";
import Link from "next/link";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
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
import { CheckCircle2, XCircle } from "lucide-react";

import { accountingApi } from "../api/accounting.api";
import { StatCard, StatusBadge, formatMoney } from "./primitives";

const cardClass =
  "rounded-[20px] border border-[var(--border)] bg-[var(--card)] p-5 shadow-[var(--shadow-sm)]";

const TYPE_META: Record<string, { label: string; color: string }> = {
  asset: { label: "Assets", color: "var(--accent)" },
  liability: { label: "Liabilities", color: "var(--warning)" },
  equity: { label: "Equity", color: "var(--info)" },
  income: { label: "Income", color: "var(--success)" },
  expense: { label: "Expenses", color: "var(--error)" },
};

type TooltipRenderProps = {
  active?: boolean;
  payload?: { name?: string; value?: number | string; payload?: { count?: number } }[];
};

function ChartTooltip({ active, payload }: TooltipRenderProps) {
  if (!active || !payload?.length) return null;
  const item = payload[0];
  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--card-elevated)] px-3 py-2 text-xs shadow-[var(--shadow-lg)]">
      <span className="text-[var(--foreground-secondary)]">
        {item.name}: {Number(item.value ?? 0)} account(s)
      </span>
    </div>
  );
}

type AxisTooltipProps = {
  active?: boolean;
  label?: string | number;
  payload?: { name?: string; value?: number | string; color?: string }[];
};

function AxisTooltip({ active, label, payload }: AxisTooltipProps) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--card-elevated)] px-3 py-2 text-xs shadow-[var(--shadow-lg)]">
      <div className="mb-1 font-semibold text-[var(--foreground)]">{label}</div>
      {payload.map((p) => (
        <div key={p.name} className="flex items-center gap-1.5 text-[var(--foreground-secondary)]">
          <span className="h-2 w-2 rounded-full" style={{ backgroundColor: p.color }} />
          {p.name}: {formatMoney(String(p.value ?? 0))}
        </div>
      ))}
    </div>
  );
}

const axisProps = {
  tick: { fill: "var(--muted)", fontSize: 11 },
  axisLine: { stroke: "var(--border)" },
  tickLine: false,
} as const;

export function AccountingOverview() {
  const { data, loading, error, refetch } = useApi(() => accountingApi.dashboard.summary());
  const { data: trends } = useApi(() => accountingApi.reports.trends({ months: 12 }));

  if (loading) {
    return (
      <div className="space-y-4">
        <StatCardsSkeleton count={4} />
        <StatCardsSkeleton count={4} />
      </div>
    );
  }

  if (error || !data) {
    return (
      <ErrorState description={error || "Couldn't load the accounting dashboard."} onRetry={refetch} />
    );
  }

  const t = data.totals;
  const trendData = (trends?.series ?? []).map((p) => ({
    label: p.label,
    revenue: Number(p.revenue),
    expenses: Number(p.expenses),
    profit: Number(p.profit),
    cash_in: Number(p.cash_in),
    cash_out: Number(p.cash_out),
  }));
  const counts = data.account_counts || {};
  const distribution = Object.entries(counts)
    .filter(([, n]) => Number(n) > 0)
    .map(([type, n]) => ({
      name: TYPE_META[type]?.label ?? type,
      value: Number(n),
      color: TYPE_META[type]?.color ?? "var(--muted)",
    }));

  return (
    <div className="space-y-5">
      {/* Position KPIs */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Total Assets" value={formatMoney(t.total_assets)} tone="accent" />
        <StatCard label="Total Liabilities" value={formatMoney(t.total_liabilities)} tone="warning" />
        <StatCard label="Total Equity" value={formatMoney(t.total_equity)} tone="accent" />
        <StatCard
          label="Net Income"
          value={formatMoney(t.net_income)}
          tone={parseFloat(t.net_income || "0") >= 0 ? "success" : "error"}
        />
        <StatCard label="Revenue" value={formatMoney(t.revenue)} tone="success" />
        <StatCard label="Expenses" value={formatMoney(t.expenses)} tone="error" />
        <StatCard label="Cash & Bank" value={formatMoney(t.cash_bank)} />
        <StatCard label="Accounts Receivable" value={formatMoney(t.accounts_receivable)} />
        <StatCard label="Accounts Payable" value={formatMoney(t.accounts_payable)} />
        <StatCard label="Working Capital" value={formatMoney(t.working_capital)} />
        <StatCard label="Current Ratio" value={t.current_ratio ?? "—"} />
        <StatCard label="Pending Approvals" value={data.pending_approvals} tone="warning" />
      </div>

      {/* Trend analytics */}
      {trendData.length > 0 ? (
        <div className="grid gap-5 lg:grid-cols-2">
          <div className={cardClass}>
            <h3 className="mb-1 text-sm font-semibold text-[var(--foreground-secondary)]">
              Revenue, Expenses & Profit
            </h3>
            <p className="mb-4 text-[11px] text-[var(--muted)]">Trailing 12 months</p>
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={trendData} margin={{ top: 4, right: 8, bottom: 0, left: -12 }}>
                  <defs>
                    <linearGradient id="gRev" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="var(--success)" stopOpacity={0.35} />
                      <stop offset="95%" stopColor="var(--success)" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="gExp" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="var(--error)" stopOpacity={0.35} />
                      <stop offset="95%" stopColor="var(--error)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                  <XAxis dataKey="label" {...axisProps} />
                  <YAxis {...axisProps} width={64} />
                  <Tooltip content={<AxisTooltip />} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Area
                    type="monotone"
                    dataKey="revenue"
                    name="Revenue"
                    stroke="var(--success)"
                    fill="url(#gRev)"
                    strokeWidth={2}
                  />
                  <Area
                    type="monotone"
                    dataKey="expenses"
                    name="Expenses"
                    stroke="var(--error)"
                    fill="url(#gExp)"
                    strokeWidth={2}
                  />
                  <Area
                    type="monotone"
                    dataKey="profit"
                    name="Profit"
                    stroke="var(--accent)"
                    fill="none"
                    strokeWidth={2}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className={cardClass}>
            <h3 className="mb-1 text-sm font-semibold text-[var(--foreground-secondary)]">
              Cash Flow
            </h3>
            <p className="mb-4 text-[11px] text-[var(--muted)]">Inflow vs outflow, trailing 12 months</p>
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={trendData} margin={{ top: 4, right: 8, bottom: 0, left: -12 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                  <XAxis dataKey="label" {...axisProps} />
                  <YAxis {...axisProps} width={64} />
                  <Tooltip content={<AxisTooltip />} cursor={{ fill: "var(--background-secondary)" }} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Bar dataKey="cash_in" name="Inflow" fill="var(--success)" radius={[3, 3, 0, 0]} />
                  <Bar dataKey="cash_out" name="Outflow" fill="var(--warning)" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      ) : null}

      {/* Accounting equation + distribution */}
      <div className="grid gap-5 lg:grid-cols-3">
        <div className={cardClass}>
          <h3 className="mb-1 text-sm font-semibold text-[var(--foreground-secondary)]">
            Accounting Equation
          </h3>
          <p className="mb-4 text-[11px] text-[var(--muted)]">Assets = Liabilities + Equity</p>
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <span className="rounded-xl bg-[var(--background-secondary)] px-3 py-2 font-semibold text-[var(--foreground)]">
              {formatMoney(t.total_assets)}
            </span>
            <span className="text-[var(--muted)]">=</span>
            <span className="rounded-xl bg-[var(--background-secondary)] px-3 py-2 font-semibold text-[var(--foreground)]">
              {formatMoney(t.total_liabilities)}
            </span>
            <span className="text-[var(--muted)]">+</span>
            <span className="rounded-xl bg-[var(--background-secondary)] px-3 py-2 font-semibold text-[var(--foreground)]">
              {formatMoney(t.total_equity)}
            </span>
          </div>
          <div className="mt-4 flex items-center gap-2">
            {data.balance_sheet_balanced ? (
              <span className="inline-flex items-center gap-1.5 text-sm font-semibold text-[var(--success)]">
                <CheckCircle2 className="h-4 w-4" /> Balance sheet is balanced
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 text-sm font-semibold text-[var(--error)]">
                <XCircle className="h-4 w-4" /> Balance sheet is out of balance
              </span>
            )}
          </div>
          <div className="mt-4 grid grid-cols-2 gap-3 border-t border-[var(--border)] pt-4 text-sm">
            <div>
              <div className="text-xs uppercase tracking-wide text-[var(--muted)]">Draft journals</div>
              <div className="mt-0.5 font-semibold text-[var(--foreground)]">{data.draft_journals}</div>
            </div>
            <div>
              <div className="text-xs uppercase tracking-wide text-[var(--muted)]">Ending cash</div>
              <div className="mt-0.5 font-semibold text-[var(--foreground)]">
                {formatMoney(t.ending_cash)}
              </div>
            </div>
          </div>
        </div>

        <div className={`${cardClass} lg:col-span-2`}>
          <h3 className="mb-1 text-sm font-semibold text-[var(--foreground-secondary)]">
            Accounts by Type
          </h3>
          <p className="mb-4 text-[11px] text-[var(--muted)]">Distribution of the chart of accounts</p>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="h-52 w-full">
              {distribution.length === 0 ? (
                <div className="grid h-full place-items-center text-sm text-[var(--muted)]">
                  No accounts yet.
                </div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={distribution}
                      cx="50%"
                      cy="50%"
                      innerRadius={45}
                      outerRadius={72}
                      paddingAngle={3}
                      dataKey="value"
                    >
                      {distribution.map((entry) => (
                        <Cell key={entry.name} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip content={<ChartTooltip />} />
                  </PieChart>
                </ResponsiveContainer>
              )}
            </div>
            <div className="space-y-1.5 self-center">
              {distribution.map((d) => (
                <div key={d.name} className="flex items-center justify-between text-xs">
                  <span className="flex items-center gap-1.5 text-[var(--foreground-secondary)]">
                    <span className="h-2 w-2 rounded-full" style={{ backgroundColor: d.color }} />
                    {d.name}
                  </span>
                  <span className="font-semibold text-[var(--foreground)]">{d.value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Recent journals */}
      <div className={cardClass}>
        <h3 className="mb-3 text-sm font-semibold text-[var(--foreground-secondary)]">
          Recent Journals
        </h3>
        {data.recent_journals.length === 0 ? (
          <p className="py-6 text-center text-sm text-[var(--muted)]">No journals recorded yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-[var(--border)] text-[var(--muted)]">
                  <th className="py-2 pr-3 font-medium">Number</th>
                  <th className="py-2 pr-3 font-medium">Date</th>
                  <th className="py-2 pr-3 font-medium">Description</th>
                  <th className="py-2 pr-3 font-medium text-right">Debit</th>
                  <th className="py-2 font-medium text-right">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border)]">
                {data.recent_journals.map((j) => (
                  <tr key={j.id}>
                    <td className="py-2.5 pr-3">
                      <Link
                        href={`/accounting/journals/${j.id}`}
                        className="font-medium text-[var(--foreground)] hover:text-[var(--accent)]"
                      >
                        {j.number}
                      </Link>
                    </td>
                    <td className="py-2.5 pr-3 text-[var(--foreground-secondary)]">{j.date}</td>
                    <td className="py-2.5 pr-3 text-[var(--foreground-secondary)]">
                      {j.description || "—"}
                    </td>
                    <td className="py-2.5 pr-3 text-right font-semibold text-[var(--foreground)]">
                      {formatMoney(j.total_debit)}
                    </td>
                    <td className="py-2.5 text-right">
                      <StatusBadge status={j.status} label={j.status_display} />
                    </td>
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
