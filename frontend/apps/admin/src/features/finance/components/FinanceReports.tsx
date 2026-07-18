"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
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
import { Button, EmptyState, Input, Select, Table, useToast } from "@hostel/ui";
import { Download } from "lucide-react";

import { financeApi } from "../api/finance.api";
import type {
  CollectionsReport,
  DuesReport,
  ExpenseBreakdownReport,
  ExportType,
  ProfitLossReport,
} from "../types/finance.types";
import { StatusBadge, formatMoney } from "./primitives";

const cardClass =
  "rounded-[20px] border border-[var(--border)] bg-[var(--card)] p-5 shadow-[var(--shadow-sm)]";

const PIE_COLORS = [
  "var(--accent)", "var(--success)", "var(--warning)", "var(--info)", "var(--error)",
  "#8b5cf6", "#ec4899", "#14b8a6", "#f97316", "#64748b",
];

const TABS = [
  { id: "collections", label: "Collections" },
  { id: "profit_loss", label: "Profit & Loss" },
  { id: "expense_breakdown", label: "Expense Breakdown" },
  { id: "dues", label: "Dues" },
] as const;
type TabId = (typeof TABS)[number]["id"];

const EXPORT_TYPES: { value: ExportType; label: string }[] = [
  { value: "transactions", label: "Transactions" },
  { value: "invoices", label: "Invoices" },
  { value: "payments", label: "Payments" },
  { value: "expenses", label: "Expenses" },
  { value: "income", label: "Income" },
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
          {(item.name ?? item.dataKey) as string}: {formatMoney(Number(item.value || 0))}
        </div>
      ))}
    </div>
  );
}

function isoDaysAgo(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}

export function FinanceReports() {
  const toast = useToast();
  const [tab, setTab] = useState<TabId>("collections");
  const [start, setStart] = useState(isoDaysAgo(30));
  const [end, setEnd] = useState(isoDaysAgo(0));
  const [exportType, setExportType] = useState<ExportType>("transactions");
  const [exporting, setExporting] = useState(false);

  const download = async () => {
    setExporting(true);
    try {
      await financeApi.reports.exportCsv(exportType);
      toast.success("Export downloaded.");
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setExporting(false);
    }
  };

  const range = { start, end };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end gap-3">
        <Input label="From" type="date" value={start} onChange={(e) => setStart(e.target.value)} />
        <Input label="To" type="date" value={end} onChange={(e) => setEnd(e.target.value)} />
      </div>

      <div className="flex flex-wrap gap-1 border-b border-[var(--border)]">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={`-mb-px border-b-2 px-4 py-2 text-sm font-medium transition ${
              t.id === tab
                ? "border-[var(--accent)] text-[var(--foreground)]"
                : "border-transparent text-[var(--muted)] hover:text-[var(--foreground)]"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "collections" && <CollectionsTab range={range} />}
      {tab === "profit_loss" && <ProfitLossTab range={range} />}
      {tab === "expense_breakdown" && <ExpenseBreakdownTab range={range} />}
      {tab === "dues" && <DuesTab />}

      <div className={cardClass}>
        <h3 className="mb-1 text-sm font-semibold text-[var(--foreground-secondary)]">Export</h3>
        <p className="mb-4 text-[11px] text-[var(--muted)]">Download a finance dataset as CSV.</p>
        <div className="flex flex-wrap items-end gap-3">
          <Select
            label="Dataset"
            value={exportType}
            onChange={(e) => setExportType(e.target.value as ExportType)}
            options={EXPORT_TYPES}
          />
          <Button loading={exporting} onClick={download}>
            <Download className="h-4 w-4" /> Download CSV
          </Button>
        </div>
      </div>
    </div>
  );
}

type Range = { start: string; end: string };

function useReport<T>(fetcher: () => Promise<T>, deps: React.DependencyList) {
  const toast = useToast();
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);

  // Keep the latest fetcher in a ref so `load` can have a literal (stable) dep
  // list; the caller-provided `deps` drives the re-run via the effect below.
  const fetcherRef = useRef(fetcher);
  useEffect(() => {
    fetcherRef.current = fetcher;
  });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setData(await fetcherRef.current());
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return { data, loading };
}

function CollectionsTab({ range }: { range: Range }) {
  const { data, loading } = useReport<CollectionsReport>(
    () => financeApi.reports.collections(range),
    [range.start, range.end],
  );

  if (loading) return <div className="text-sm text-[var(--muted)]">Loading…</div>;
  if (!data || data.rows.length === 0) {
    return <EmptyState title="No collections" description="No payments were collected in this range." />;
  }

  const chart = data.rows.map((r) => ({ date: r.date, Collected: Number(r.total) }));

  return (
    <div className="space-y-4">
      <div className={cardClass}>
        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chart} margin={{ top: 5, right: 5, left: -10, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" />
              <XAxis dataKey="date" tickLine={false} tick={{ fontSize: 11, fill: "var(--muted)" }} />
              <YAxis tickLine={false} tick={{ fontSize: 11, fill: "var(--muted)" }} />
              <Tooltip content={<ChartTooltip />} cursor={{ fill: "var(--background-secondary)" }} />
              <Bar dataKey="Collected" fill="var(--accent)" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
      <Table>
        <thead>
          <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
            <th className="px-4 py-3 font-medium">Date</th>
            <th className="px-4 py-3 font-medium text-right">Payments</th>
            <th className="px-4 py-3 font-medium text-right">Total</th>
          </tr>
        </thead>
        <tbody>
          {data.rows.map((r) => (
            <tr key={r.date} className="border-b border-[var(--border)] last:border-0">
              <td className="px-4 py-3 text-[var(--foreground)]">{r.date}</td>
              <td className="px-4 py-3 text-right text-[var(--foreground-secondary)]">{r.count}</td>
              <td className="px-4 py-3 text-right font-medium text-[var(--foreground)]">{formatMoney(r.total)}</td>
            </tr>
          ))}
        </tbody>
      </Table>
    </div>
  );
}

function ProfitLossTab({ range }: { range: Range }) {
  const { data, loading } = useReport<ProfitLossReport>(
    () => financeApi.reports.profitLoss(range),
    [range.start, range.end],
  );

  if (loading) return <div className="text-sm text-[var(--muted)]">Loading…</div>;
  if (!data) return <EmptyState title="No data" description="No transactions in this range." />;

  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-3">
        <div className={cardClass}>
          <div className="text-xs uppercase tracking-wide text-[var(--muted)]">Total Income</div>
          <div className="mt-1 text-2xl font-semibold text-[var(--success)]">{formatMoney(data.total_income)}</div>
        </div>
        <div className={cardClass}>
          <div className="text-xs uppercase tracking-wide text-[var(--muted)]">Total Expenses</div>
          <div className="mt-1 text-2xl font-semibold text-[var(--error)]">{formatMoney(data.total_expenses)}</div>
        </div>
        <div className={cardClass}>
          <div className="text-xs uppercase tracking-wide text-[var(--muted)]">Net</div>
          <div className="mt-1 text-2xl font-semibold text-[var(--accent)]">{formatMoney(data.net)}</div>
        </div>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <PlList title="Income" rows={data.income} tone="var(--success)" />
        <PlList title="Expenses" rows={data.expenses} tone="var(--error)" />
      </div>
    </div>
  );
}

function PlList({
  title,
  rows,
  tone,
}: {
  title: string;
  rows: { category: string; total: string }[];
  tone: string;
}) {
  return (
    <div className={cardClass}>
      <h3 className="mb-3 text-sm font-semibold text-[var(--foreground-secondary)]">{title}</h3>
      {rows.length === 0 ? (
        <p className="py-4 text-center text-sm text-[var(--muted)]">Nothing to show.</p>
      ) : (
        <div className="space-y-1.5">
          {rows.map((r) => (
            <div key={r.category} className="flex items-center justify-between text-sm">
              <span className="capitalize text-[var(--foreground-secondary)]">{r.category.replace(/[:_]/g, " ")}</span>
              <span className="font-semibold" style={{ color: tone }}>{formatMoney(r.total)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ExpenseBreakdownTab({ range }: { range: Range }) {
  const { data, loading } = useReport<ExpenseBreakdownReport>(
    () => financeApi.reports.expenseBreakdown(range),
    [range.start, range.end],
  );

  if (loading) return <div className="text-sm text-[var(--muted)]">Loading…</div>;
  if (!data || data.rows.length === 0) {
    return <EmptyState title="No expenses" description="No paid expenses in this range." />;
  }

  const pie = data.rows.map((r) => ({ name: r.category, value: Number(r.total) }));

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <div className={cardClass}>
        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={pie} cx="50%" cy="50%" innerRadius={50} outerRadius={80} paddingAngle={3} dataKey="value">
                {pie.map((entry, i) => (
                  <Cell key={entry.name} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip content={<ChartTooltip />} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>
      <Table>
        <thead>
          <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
            <th className="px-4 py-3 font-medium">Category</th>
            <th className="px-4 py-3 font-medium text-right">Count</th>
            <th className="px-4 py-3 font-medium text-right">Total</th>
          </tr>
        </thead>
        <tbody>
          {data.rows.map((r) => (
            <tr key={r.category} className="border-b border-[var(--border)] last:border-0">
              <td className="px-4 py-3 text-[var(--foreground)]">{r.category}</td>
              <td className="px-4 py-3 text-right text-[var(--foreground-secondary)]">{r.count}</td>
              <td className="px-4 py-3 text-right font-medium text-[var(--foreground)]">{formatMoney(r.total)}</td>
            </tr>
          ))}
        </tbody>
      </Table>
    </div>
  );
}

function DuesTab() {
  const { data, loading } = useReport<DuesReport>(() => financeApi.reports.dues(), []);

  if (loading) return <div className="text-sm text-[var(--muted)]">Loading…</div>;
  if (!data || data.rows.length === 0) {
    return <EmptyState title="No outstanding dues" description="Every invoice is settled." />;
  }

  return (
    <Table>
      <thead>
        <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
          <th className="px-4 py-3 font-medium">Invoice</th>
          <th className="px-4 py-3 font-medium">Resident</th>
          <th className="px-4 py-3 font-medium">Due</th>
          <th className="px-4 py-3 font-medium text-right">Total</th>
          <th className="px-4 py-3 font-medium text-right">Paid</th>
          <th className="px-4 py-3 font-medium text-right">Balance</th>
          <th className="px-4 py-3 font-medium">Status</th>
        </tr>
      </thead>
      <tbody>
        {data.rows.map((r) => (
          <tr key={r.id} className="border-b border-[var(--border)] last:border-0">
            <td className="px-4 py-3 font-medium text-[var(--foreground)]">{r.number}</td>
            <td className="px-4 py-3 text-[var(--foreground-secondary)]">{r.resident_name}</td>
            <td className="px-4 py-3 text-[var(--foreground-secondary)]">{r.due_date || "—"}</td>
            <td className="px-4 py-3 text-right text-[var(--foreground-secondary)]">{formatMoney(r.total)}</td>
            <td className="px-4 py-3 text-right text-[var(--foreground-secondary)]">{formatMoney(r.paid_amount)}</td>
            <td className="px-4 py-3 text-right font-semibold text-[var(--foreground)]">{formatMoney(r.balance)}</td>
            <td className="px-4 py-3"><StatusBadge status={r.status} /></td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}
