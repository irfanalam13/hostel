"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { Button, EmptyState, Input, Select, Table, useToast } from "@hostel/ui";
import { CheckCircle2, Download, XCircle } from "lucide-react";

import { accountingApi } from "../api/accounting.api";
import type {
  BalanceSheetReport,
  CashFlowReport,
  JournalRegisterReport,
  ProfitLossReport,
  ReportExportType,
  StatementOfEquityReport,
  TrialBalanceReport,
} from "../types/accounting.types";
import { StatCard, formatMoney } from "./primitives";

const cardClass =
  "rounded-[20px] border border-[var(--border)] bg-[var(--card)] p-5 shadow-[var(--shadow-sm)]";

const TABS = [
  { id: "trial_balance", label: "Trial Balance" },
  { id: "profit_loss", label: "Profit & Loss" },
  { id: "balance_sheet", label: "Balance Sheet" },
  { id: "equity", label: "Statement of Equity" },
  { id: "cash_flow", label: "Cash Flow" },
  { id: "journal_register", label: "Journal Register" },
] as const;
type TabId = (typeof TABS)[number]["id"];

const EXPORT_TYPES: { value: ReportExportType; label: string }[] = [
  { value: "trial-balance", label: "Trial Balance" },
  { value: "general-ledger", label: "General Ledger" },
  { value: "profit-loss", label: "Profit & Loss" },
  { value: "balance-sheet", label: "Balance Sheet" },
  { value: "journal-register", label: "Journal Register" },
];

function isoDaysAgo(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}

function BalancedFlag({ balanced }: { balanced: boolean }) {
  return balanced ? (
    <span className="inline-flex items-center gap-1.5 text-sm font-semibold text-[var(--success)]">
      <CheckCircle2 className="h-4 w-4" /> Balanced
    </span>
  ) : (
    <span className="inline-flex items-center gap-1.5 text-sm font-semibold text-[var(--error)]">
      <XCircle className="h-4 w-4" /> Out of balance
    </span>
  );
}

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

export function Statements() {
  const toast = useToast();
  const [tab, setTab] = useState<TabId>("trial_balance");
  const [start, setStart] = useState(isoDaysAgo(30));
  const [end, setEnd] = useState(isoDaysAgo(0));
  const [exportType, setExportType] = useState<ReportExportType>("trial-balance");
  const [exporting, setExporting] = useState(false);

  const download = async () => {
    setExporting(true);
    try {
      await accountingApi.reports.exportCsv(exportType);
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

      {tab === "trial_balance" && <TrialBalanceTab end={end} />}
      {tab === "profit_loss" && <ProfitLossTab range={range} />}
      {tab === "balance_sheet" && <BalanceSheetTab end={end} />}
      {tab === "equity" && <StatementOfEquityTab range={range} />}
      {tab === "cash_flow" && <CashFlowTab range={range} />}
      {tab === "journal_register" && <JournalRegisterTab range={range} />}

      <div className={cardClass}>
        <h3 className="mb-1 text-sm font-semibold text-[var(--foreground-secondary)]">Export</h3>
        <p className="mb-4 text-[11px] text-[var(--muted)]">Download an accounting dataset as CSV.</p>
        <div className="flex flex-wrap items-end gap-3">
          <Select
            label="Dataset"
            value={exportType}
            onChange={(e) => setExportType(e.target.value as ReportExportType)}
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

function TrialBalanceTab({ end }: { end: string }) {
  const { data, loading } = useReport<TrialBalanceReport>(
    () => accountingApi.reports.trialBalance({ end }),
    [end],
  );

  if (loading) return <div className="text-sm text-[var(--muted)]">Loading…</div>;
  if (!data || data.rows.length === 0) {
    return <EmptyState title="No data" description="No account balances to report as of this date." />;
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-sm text-[var(--muted)]">As of {data.as_of}</span>
        <BalancedFlag balanced={data.balanced} />
      </div>
      <Table>
        <thead>
          <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
            <th className="px-4 py-3 font-medium">Code</th>
            <th className="px-4 py-3 font-medium">Account</th>
            <th className="px-4 py-3 font-medium">Type</th>
            <th className="px-4 py-3 font-medium text-right">Debit</th>
            <th className="px-4 py-3 font-medium text-right">Credit</th>
          </tr>
        </thead>
        <tbody>
          {data.rows.map((r) => (
            <tr key={r.account_id} className="border-b border-[var(--border)] last:border-0">
              <td className="px-4 py-3 font-mono text-[var(--foreground-secondary)]">{r.code}</td>
              <td className="px-4 py-3 text-[var(--foreground)]">{r.name}</td>
              <td className="px-4 py-3 capitalize text-[var(--foreground-secondary)]">{r.type}</td>
              <td className="px-4 py-3 text-right text-[var(--foreground-secondary)]">
                {parseFloat(r.debit || "0") ? formatMoney(r.debit) : "—"}
              </td>
              <td className="px-4 py-3 text-right text-[var(--foreground-secondary)]">
                {parseFloat(r.credit || "0") ? formatMoney(r.credit) : "—"}
              </td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr className="font-semibold text-[var(--foreground)]">
            <td className="px-4 py-3" colSpan={3}>
              Totals
            </td>
            <td className="px-4 py-3 text-right">{formatMoney(data.total_debit)}</td>
            <td className="px-4 py-3 text-right">{formatMoney(data.total_credit)}</td>
          </tr>
        </tfoot>
      </Table>
    </div>
  );
}

function StatementList({
  title,
  rows,
  tone,
}: {
  title: string;
  rows: { code: string; name: string; amount: string }[];
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
            <div key={r.code} className="flex items-center justify-between text-sm">
              <span className="text-[var(--foreground-secondary)]">
                <span className="font-mono text-[var(--muted)]">{r.code}</span> {r.name}
              </span>
              <span className="font-semibold" style={{ color: tone }}>
                {formatMoney(r.amount)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ProfitLossTab({ range }: { range: Range }) {
  const { data, loading } = useReport<ProfitLossReport>(
    () => accountingApi.reports.profitLoss(range),
    [range.start, range.end],
  );

  if (loading) return <div className="text-sm text-[var(--muted)]">Loading…</div>;
  if (!data) return <EmptyState title="No data" description="No transactions in this range." />;

  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard label="Total Income" value={formatMoney(data.total_income)} tone="success" />
        <StatCard label="Total Expenses" value={formatMoney(data.total_expenses)} tone="error" />
        <StatCard label="Net Profit" value={formatMoney(data.net_profit)} tone="accent" />
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <StatementList title="Income" rows={data.income} tone="var(--success)" />
        <StatementList title="Expenses" rows={data.expenses} tone="var(--error)" />
      </div>
    </div>
  );
}

function BalanceSheetTab({ end }: { end: string }) {
  const { data, loading } = useReport<BalanceSheetReport>(
    () => accountingApi.reports.balanceSheet({ end }),
    [end],
  );

  if (loading) return <div className="text-sm text-[var(--muted)]">Loading…</div>;
  if (!data) return <EmptyState title="No data" description="No balances to report as of this date." />;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <span className="text-sm text-[var(--muted)]">As of {data.as_of}</span>
        <BalancedFlag balanced={data.balanced} />
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        <StatementList title="Assets" rows={data.assets} tone="var(--accent)" />
        <StatementList title="Liabilities" rows={data.liabilities} tone="var(--warning)" />
        <StatementList title="Equity" rows={data.equity} tone="var(--info)" />
      </div>
      <div className={cardClass}>
        <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
          <span className="text-[var(--foreground-secondary)]">Accounting equation</span>
          <span className="flex flex-wrap items-center gap-2 font-semibold text-[var(--foreground)]">
            <span>{formatMoney(data.total_assets)}</span>
            <span className="text-[var(--muted)]">=</span>
            <span>{formatMoney(data.total_liabilities)}</span>
            <span className="text-[var(--muted)]">+</span>
            <span>{formatMoney(data.total_equity)}</span>
          </span>
        </div>
      </div>
    </div>
  );
}

function CashFlowTab({ range }: { range: Range }) {
  const { data, loading } = useReport<CashFlowReport>(
    () => accountingApi.reports.cashFlow(range),
    [range.start, range.end],
  );

  if (loading) return <div className="text-sm text-[var(--muted)]">Loading…</div>;
  if (!data) return <EmptyState title="No data" description="No cash movement in this range." />;

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
      <StatCard label="Beginning Cash" value={formatMoney(data.beginning_cash)} />
      <StatCard label="Inflow" value={formatMoney(data.inflow)} tone="success" />
      <StatCard label="Outflow" value={formatMoney(data.outflow)} tone="error" />
      <StatCard
        label="Net Change"
        value={formatMoney(data.net_change)}
        tone={parseFloat(data.net_change || "0") >= 0 ? "success" : "error"}
      />
      <StatCard label="Ending Cash" value={formatMoney(data.ending_cash)} tone="accent" />
    </div>
  );
}

function StatementOfEquityTab({ range }: { range: Range }) {
  const { data, loading } = useReport<StatementOfEquityReport>(
    () => accountingApi.reports.statementOfEquity(range),
    [range.start, range.end],
  );

  if (loading) return <div className="text-sm text-[var(--muted)]">Loading…</div>;
  if (!data || data.components.length === 0) {
    return <EmptyState title="No data" description="No equity movement in this range." />;
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard label="Opening Equity" value={formatMoney(data.opening_equity)} />
        <StatCard label="Net Income" value={formatMoney(data.net_income)} tone="success" />
        <StatCard label="Closing Equity" value={formatMoney(data.closing_equity)} tone="accent" />
      </div>
      <Table>
        <thead>
          <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
            <th className="px-4 py-3 font-medium">Code</th>
            <th className="px-4 py-3 font-medium">Component</th>
            <th className="px-4 py-3 font-medium text-right">Opening</th>
            <th className="px-4 py-3 font-medium text-right">Movement</th>
            <th className="px-4 py-3 font-medium text-right">Closing</th>
          </tr>
        </thead>
        <tbody>
          {data.components.map((c) => (
            <tr key={c.code} className="border-b border-[var(--border)] last:border-0">
              <td className="px-4 py-3 font-mono text-[var(--foreground-secondary)]">{c.code}</td>
              <td className="px-4 py-3 text-[var(--foreground)]">{c.name}</td>
              <td className="px-4 py-3 text-right text-[var(--foreground-secondary)]">
                {formatMoney(c.opening)}
              </td>
              <td className="px-4 py-3 text-right text-[var(--foreground-secondary)]">
                {formatMoney(c.movement)}
              </td>
              <td className="px-4 py-3 text-right font-semibold text-[var(--foreground)]">
                {formatMoney(c.closing)}
              </td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr className="font-semibold text-[var(--foreground)]">
            <td className="px-4 py-3" colSpan={2}>
              Total Equity
            </td>
            <td className="px-4 py-3 text-right">{formatMoney(data.opening_equity)}</td>
            <td className="px-4 py-3 text-right">{formatMoney(data.movement)}</td>
            <td className="px-4 py-3 text-right">{formatMoney(data.closing_equity)}</td>
          </tr>
        </tfoot>
      </Table>
    </div>
  );
}

function JournalRegisterTab({ range }: { range: Range }) {
  const { data, loading } = useReport<JournalRegisterReport>(
    () => accountingApi.reports.journalRegister(range),
    [range.start, range.end],
  );

  if (loading) return <div className="text-sm text-[var(--muted)]">Loading…</div>;
  if (!data || data.rows.length === 0) {
    return <EmptyState title="No journals" description="No journals were posted in this range." />;
  }

  return (
    <Table>
      <thead>
        <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
          <th className="px-4 py-3 font-medium">Number</th>
          <th className="px-4 py-3 font-medium">Date</th>
          <th className="px-4 py-3 font-medium">Description</th>
          <th className="px-4 py-3 font-medium">Type</th>
          <th className="px-4 py-3 font-medium text-right">Amount</th>
        </tr>
      </thead>
      <tbody>
        {data.rows.map((r) => (
          <tr key={r.id} className="border-b border-[var(--border)] last:border-0">
            <td className="px-4 py-3 font-medium text-[var(--foreground)]">{r.number}</td>
            <td className="px-4 py-3 text-[var(--foreground-secondary)]">{r.date}</td>
            <td className="px-4 py-3 text-[var(--foreground-secondary)]">{r.description || "—"}</td>
            <td className="px-4 py-3 capitalize text-[var(--foreground-secondary)]">
              {r.type.replace(/_/g, " ")}
            </td>
            <td className="px-4 py-3 text-right font-semibold text-[var(--foreground)]">
              {formatMoney(r.amount)}
            </td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}
