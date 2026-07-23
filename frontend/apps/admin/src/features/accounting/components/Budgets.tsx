"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  Button,
  EmptyState,
  Input,
  Modal,
  Select,
  Table,
  useConfirm,
  useToast,
} from "@hostel/ui";
import { BarChart3, Check, Plus, Trash2 } from "lucide-react";

import { accountingApi } from "../api/accounting.api";
import type {
  Account,
  Budget,
  BudgetPayload,
  BudgetPeriodType,
  BudgetVarianceReport,
  FiscalYear,
} from "../types/accounting.types";
import { BUDGET_PERIOD_TYPES, StatCard, StatusBadge, formatMoney } from "./primitives";

type LineForm = { account: string; amount: string };
const emptyLine: LineForm = { account: "", amount: "0" };

const num = (v: string) => {
  const n = parseFloat(v);
  return Number.isFinite(n) ? n : 0;
};

export function Budgets() {
  const toast = useToast();
  const confirm = useConfirm();

  const [rows, setRows] = useState<Budget[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [years, setYears] = useState<FiscalYear[]>([]);
  const [loading, setLoading] = useState(true);

  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [name, setName] = useState("");
  const [fiscalYear, setFiscalYear] = useState("");
  const [periodType, setPeriodType] = useState<BudgetPeriodType>("annual");
  const [lines, setLines] = useState<LineForm[]>([{ ...emptyLine }]);

  const [variance, setVariance] = useState<BudgetVarianceReport | null>(null);
  const [varianceOpen, setVarianceOpen] = useState(false);
  const [varianceLoading, setVarianceLoading] = useState(false);

  const viewVariance = async (b: Budget) => {
    setVarianceOpen(true);
    setVariance(null);
    setVarianceLoading(true);
    try {
      setVariance(await accountingApi.budgets.variance(b.id));
    } catch (e) {
      toast.error((e as Error).message);
      setVarianceOpen(false);
    } finally {
      setVarianceLoading(false);
    }
  };

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows(await accountingApi.budgets.list());
    } catch (e) {
      toast.error((e as Error).message, "Couldn't load budgets");
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    load();
    accountingApi.accounts
      .list({ is_group: "false", ordering: "code" })
      .then(setAccounts)
      .catch(() => {});
    accountingApi.fiscalYears.list().then(setYears).catch(() => {});
  }, [load]);

  const setLine = (i: number, patch: Partial<LineForm>) =>
    setLines((ls) => ls.map((l, idx) => (idx === i ? { ...l, ...patch } : l)));

  const total = useMemo(() => lines.reduce((s, l) => s + num(l.amount), 0), [lines]);

  const startCreate = () => {
    setName("");
    setFiscalYear(years[0]?.id ?? "");
    setPeriodType("annual");
    setLines([{ ...emptyLine }]);
    setOpen(true);
  };

  const submit = async () => {
    if (!name.trim() || !fiscalYear) {
      toast.error("Name and fiscal year are required.");
      return;
    }
    const cleanLines = lines
      .filter((l) => l.account && num(l.amount) !== 0)
      .map((l) => ({ account: l.account, amount: l.amount }));
    if (cleanLines.length === 0) {
      toast.error("Add at least one budget line.");
      return;
    }
    setBusy(true);
    try {
      const body: BudgetPayload = {
        name: name.trim(),
        fiscal_year: fiscalYear,
        period_type: periodType,
        lines: cleanLines,
      };
      await accountingApi.budgets.create(body);
      toast.success("Budget created.");
      setOpen(false);
      await load();
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const act = async (fn: () => Promise<unknown>, ok: string) => {
    try {
      await fn();
      toast.success(ok);
      await load();
    } catch (e) {
      toast.error((e as Error).message);
    }
  };

  const remove = async (b: Budget) => {
    const yes = await confirm({
      title: "Delete budget",
      message: `Delete "${b.name}"?`,
      danger: true,
      confirmText: "Delete",
    });
    if (yes) await act(() => accountingApi.budgets.remove(b.id), "Budget deleted.");
  };

  const budgetTotal = (b: Budget) => b.lines.reduce((s, l) => s + num(l.amount), 0);

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button onClick={startCreate}>
          <Plus className="h-4 w-4" /> New budget
        </Button>
      </div>

      {loading ? (
        <div className="text-sm text-[var(--muted)]">Loading…</div>
      ) : rows.length === 0 ? (
        <EmptyState title="No budgets" description="Plan account budgets and route them through approval." />
      ) : (
        <Table>
          <thead>
            <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
              <th className="px-4 py-3 font-medium">Name</th>
              <th className="px-4 py-3 font-medium">Period</th>
              <th className="px-4 py-3 font-medium text-right">Lines</th>
              <th className="px-4 py-3 font-medium text-right">Total</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((b) => (
              <tr key={b.id} className="border-b border-[var(--border)] last:border-0">
                <td className="px-4 py-3 font-medium text-[var(--foreground)]">{b.name}</td>
                <td className="px-4 py-3 capitalize text-[var(--foreground-secondary)]">{b.period_type}</td>
                <td className="px-4 py-3 text-right text-[var(--foreground-secondary)]">{b.lines.length}</td>
                <td className="px-4 py-3 text-right font-semibold text-[var(--foreground)]">
                  {formatMoney(budgetTotal(b))}
                </td>
                <td className="px-4 py-3">
                  <StatusBadge
                    status={b.is_approved ? "approved" : "draft"}
                    label={b.is_approved ? "Approved" : "Draft"}
                  />
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center justify-end gap-1">
                    <Button variant="ghost" size="sm" title="Variance analysis" onClick={() => viewVariance(b)}>
                      <BarChart3 className="h-4 w-4 text-[var(--accent)]" />
                    </Button>
                    {!b.is_approved ? (
                      <Button
                        variant="ghost"
                        size="sm"
                        title="Approve"
                        onClick={() => act(() => accountingApi.budgets.approve(b.id), "Budget approved.")}
                      >
                        <Check className="h-4 w-4 text-[var(--success)]" />
                      </Button>
                    ) : null}
                    <Button variant="ghost" size="sm" title="Delete" onClick={() => remove(b)}>
                      <Trash2 className="h-4 w-4 text-[var(--error)]" />
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      <Modal open={open} title="New budget" onClose={() => setOpen(false)}>
        <div className="max-h-[74vh] space-y-3 overflow-y-auto pr-1">
          <Input label="Name" value={name} onChange={(e) => setName(e.target.value)} />
          <div className="grid grid-cols-2 gap-3">
            <Select
              label="Fiscal year"
              value={fiscalYear}
              onChange={(e) => setFiscalYear(e.target.value)}
              placeholder="Select fiscal year"
            >
              {years.map((y) => (
                <option key={y.id} value={y.id}>
                  {y.name}
                </option>
              ))}
            </Select>
            <Select
              label="Period type"
              value={periodType}
              onChange={(e) => setPeriodType(e.target.value as BudgetPeriodType)}
              options={BUDGET_PERIOD_TYPES}
            />
          </div>

          <section className="space-y-2">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">Lines</h3>
              <Button variant="ghost" size="sm" onClick={() => setLines((ls) => [...ls, { ...emptyLine }])}>
                <Plus className="h-4 w-4" /> Add line
              </Button>
            </div>
            {lines.map((l, i) => (
              <div key={i} className="grid grid-cols-[1fr_auto_auto] items-end gap-2">
                <Select
                  label="Account"
                  value={l.account}
                  onChange={(e) => setLine(i, { account: e.target.value })}
                  placeholder="Select account"
                >
                  {accounts.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.code} · {a.name}
                    </option>
                  ))}
                </Select>
                <Input
                  label="Amount"
                  type="number"
                  value={l.amount}
                  onChange={(e) => setLine(i, { amount: e.target.value })}
                />
                {lines.length > 1 ? (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setLines((ls) => ls.filter((_, idx) => idx !== i))}
                  >
                    <Trash2 className="h-4 w-4 text-[var(--error)]" />
                  </Button>
                ) : (
                  <div />
                )}
              </div>
            ))}
          </section>

          <div className="flex items-center justify-between rounded-xl bg-[var(--background-secondary)] px-3 py-2 text-sm">
            <span className="text-[var(--foreground-secondary)]">Total budget</span>
            <span className="font-semibold text-[var(--foreground)]">{formatMoney(total)}</span>
          </div>

          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button loading={busy} onClick={submit}>
              Create
            </Button>
          </div>
        </div>
      </Modal>

      <Modal
        open={varianceOpen}
        title={variance ? `Variance — ${variance.name}` : "Budget variance"}
        onClose={() => setVarianceOpen(false)}
      >
        <div className="max-h-[74vh] space-y-3 overflow-y-auto pr-1">
          {varianceLoading || !variance ? (
            <div className="text-sm text-[var(--muted)]">Loading…</div>
          ) : variance.rows.length === 0 ? (
            <EmptyState title="No budget lines" description="This budget has no lines to analyse." />
          ) : (
            <>
              <p className="text-[11px] text-[var(--muted)]">
                Actual ledger activity for {variance.fiscal_year}. Variance is favourable when
                positive (income above plan, expenses under plan).
              </p>
              <div className="grid grid-cols-3 gap-3">
                <StatCard label="Budgeted" value={formatMoney(variance.total_budget)} />
                <StatCard label="Actual" value={formatMoney(variance.total_actual)} />
                <StatCard
                  label="Variance"
                  value={formatMoney(variance.total_variance)}
                  tone={num(variance.total_variance) >= 0 ? "success" : "error"}
                />
              </div>
              <Table>
                <thead>
                  <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
                    <th className="px-3 py-2 font-medium">Account</th>
                    <th className="px-3 py-2 font-medium text-right">Budget</th>
                    <th className="px-3 py-2 font-medium text-right">Actual</th>
                    <th className="px-3 py-2 font-medium text-right">Variance</th>
                    <th className="px-3 py-2 font-medium text-right">Used</th>
                  </tr>
                </thead>
                <tbody>
                  {variance.rows.map((r) => (
                    <tr key={r.account_id} className="border-b border-[var(--border)] last:border-0">
                      <td className="px-3 py-2 text-[var(--foreground)]">
                        <span className="font-mono text-[var(--muted)]">{r.code}</span> {r.name}
                      </td>
                      <td className="px-3 py-2 text-right text-[var(--foreground-secondary)]">
                        {formatMoney(r.budget)}
                      </td>
                      <td className="px-3 py-2 text-right text-[var(--foreground-secondary)]">
                        {formatMoney(r.actual)}
                      </td>
                      <td
                        className="px-3 py-2 text-right font-semibold"
                        style={{ color: num(r.variance) >= 0 ? "var(--success)" : "var(--error)" }}
                      >
                        {formatMoney(r.variance)}
                      </td>
                      <td className="px-3 py-2 text-right text-[var(--foreground-secondary)]">
                        {r.utilization != null ? `${r.utilization}%` : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            </>
          )}
          <div className="flex justify-end">
            <Button variant="ghost" onClick={() => setVarianceOpen(false)}>
              Close
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
