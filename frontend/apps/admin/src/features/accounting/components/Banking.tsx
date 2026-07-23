"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  Button,
  EmptyState,
  Input,
  Modal,
  Select,
  Table,
  Textarea,
  useConfirm,
  useToast,
} from "@hostel/ui";
import { CheckCircle2, Pencil, Plus, RotateCcw, Trash2, Upload, Wand2 } from "lucide-react";

import { accountingApi } from "../api/accounting.api";
import type {
  Account,
  BankAccount,
  BankAccountPayload,
  BankStatementLine,
} from "../types/accounting.types";
import { StatusBadge, formatMoney } from "./primitives";

const TABS = [
  { id: "accounts", label: "Bank Accounts" },
  { id: "reconciliation", label: "Reconciliation" },
] as const;
type TabId = (typeof TABS)[number]["id"];

export function Banking() {
  const [tab, setTab] = useState<TabId>("accounts");

  return (
    <div className="space-y-4">
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

      {tab === "accounts" && <BankAccountsTab />}
      {tab === "reconciliation" && <ReconciliationTab />}
    </div>
  );
}

/* ----------------------------- Bank accounts ----------------------------- */

type BankForm = {
  name: string;
  account: string;
  bank_name: string;
  account_number: string;
  is_active: boolean;
};

const emptyBank: BankForm = {
  name: "",
  account: "",
  bank_name: "",
  account_number: "",
  is_active: true,
};

function BankAccountsTab() {
  const toast = useToast();
  const confirm = useConfirm();

  const [rows, setRows] = useState<BankAccount[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<BankAccount | null>(null);
  const [form, setForm] = useState<BankForm>(emptyBank);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows(await accountingApi.bankAccounts.list());
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    load();
    accountingApi.accounts
      .list({ type: "asset", is_group: "false", ordering: "code" })
      .then(setAccounts)
      .catch(() => {});
  }, [load]);

  const set = (patch: Partial<BankForm>) => setForm((f) => ({ ...f, ...patch }));

  const startCreate = () => {
    setEditing(null);
    setForm(emptyBank);
    setOpen(true);
  };
  const startEdit = (b: BankAccount) => {
    setEditing(b);
    setForm({
      name: b.name,
      account: b.account,
      bank_name: b.bank_name,
      account_number: b.account_number,
      is_active: b.is_active,
    });
    setOpen(true);
  };

  const submit = async () => {
    if (!form.name.trim() || !form.account) {
      toast.error("Name and linked GL account are required.");
      return;
    }
    setBusy(true);
    try {
      const body: BankAccountPayload = {
        name: form.name.trim(),
        account: form.account,
        bank_name: form.bank_name,
        account_number: form.account_number,
        is_active: form.is_active,
      };
      if (editing) await accountingApi.bankAccounts.update(editing.id, body);
      else await accountingApi.bankAccounts.create(body);
      toast.success(editing ? "Bank account updated." : "Bank account created.");
      setOpen(false);
      await load();
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const remove = async (b: BankAccount) => {
    const yes = await confirm({
      title: "Delete bank account",
      message: `Delete "${b.name}"?`,
      danger: true,
      confirmText: "Delete",
    });
    if (!yes) return;
    try {
      await accountingApi.bankAccounts.remove(b.id);
      toast.success("Bank account deleted.");
      await load();
    } catch (e) {
      toast.error((e as Error).message);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button onClick={startCreate}>
          <Plus className="h-4 w-4" /> New bank account
        </Button>
      </div>
      {loading ? (
        <div className="text-sm text-[var(--muted)]">Loading…</div>
      ) : rows.length === 0 ? (
        <EmptyState title="No bank accounts" description="Link a bank account to a GL account for reconciliation." />
      ) : (
        <Table>
          <thead>
            <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
              <th className="px-4 py-3 font-medium">Name</th>
              <th className="px-4 py-3 font-medium">Bank</th>
              <th className="px-4 py-3 font-medium">Account no.</th>
              <th className="px-4 py-3 font-medium">GL account</th>
              <th className="px-4 py-3 font-medium">Active</th>
              <th className="px-4 py-3 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((b) => (
              <tr key={b.id} className="border-b border-[var(--border)] last:border-0">
                <td className="px-4 py-3 font-medium text-[var(--foreground)]">{b.name}</td>
                <td className="px-4 py-3 text-[var(--foreground-secondary)]">{b.bank_name || "—"}</td>
                <td className="px-4 py-3 text-[var(--foreground-secondary)]">{b.account_number || "—"}</td>
                <td className="px-4 py-3 text-[var(--foreground-secondary)]">{b.account_name}</td>
                <td className="px-4 py-3">
                  <StatusBadge
                    status={b.is_active ? "active" : "inactive"}
                    label={b.is_active ? "Active" : "Inactive"}
                  />
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center justify-end gap-1">
                    <Button variant="ghost" size="sm" title="Edit" onClick={() => startEdit(b)}>
                      <Pencil className="h-4 w-4" />
                    </Button>
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

      <Modal open={open} title={editing ? "Edit bank account" : "New bank account"} onClose={() => setOpen(false)}>
        <div className="space-y-3">
          <Input label="Name" value={form.name} onChange={(e) => set({ name: e.target.value })} />
          <Select
            label="Linked GL account"
            value={form.account}
            onChange={(e) => set({ account: e.target.value })}
            placeholder="Select account"
          >
            {accounts.map((a) => (
              <option key={a.id} value={a.id}>
                {a.code} · {a.name}
              </option>
            ))}
          </Select>
          <div className="grid grid-cols-2 gap-3">
            <Input label="Bank name" value={form.bank_name} onChange={(e) => set({ bank_name: e.target.value })} />
            <Input
              label="Account number"
              value={form.account_number}
              onChange={(e) => set({ account_number: e.target.value })}
            />
          </div>
          <label className="flex items-center gap-2 text-sm text-[var(--foreground-secondary)]">
            <input type="checkbox" checked={form.is_active} onChange={(e) => set({ is_active: e.target.checked })} />
            Active
          </label>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button loading={busy} onClick={submit}>
              {editing ? "Save" : "Create"}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}

/* ----------------------------- Reconciliation ---------------------------- */

type StatementForm = { date: string; description: string; reference: string; amount: string };
const emptyStatement: StatementForm = { date: "", description: "", reference: "", amount: "0" };

function ReconciliationTab() {
  const toast = useToast();
  const confirm = useConfirm();

  const [banks, setBanks] = useState<BankAccount[]>([]);
  const [bankId, setBankId] = useState("");
  const [lines, setLines] = useState<BankStatementLine[]>([]);
  const [loading, setLoading] = useState(false);

  const [open, setOpen] = useState(false);
  const [form, setForm] = useState<StatementForm>(emptyStatement);
  const [busy, setBusy] = useState(false);

  const [importOpen, setImportOpen] = useState(false);
  const [csvText, setCsvText] = useState("");
  const [importing, setImporting] = useState(false);
  const [matching, setMatching] = useState(false);

  useEffect(() => {
    accountingApi.bankAccounts
      .list()
      .then((b) => {
        setBanks(b);
        if (b[0]) setBankId((prev) => prev || b[0].id);
      })
      .catch(() => {});
  }, []);

  const load = useCallback(async () => {
    if (!bankId) {
      setLines([]);
      return;
    }
    setLoading(true);
    try {
      setLines(await accountingApi.bankStatementLines.list({ bank_account: bankId }));
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [bankId, toast]);

  useEffect(() => {
    load();
  }, [load]);

  const set = (patch: Partial<StatementForm>) => setForm((f) => ({ ...f, ...patch }));

  const act = async (fn: () => Promise<unknown>, ok: string) => {
    try {
      await fn();
      toast.success(ok);
      await load();
    } catch (e) {
      toast.error((e as Error).message);
    }
  };

  const addLine = async () => {
    if (!bankId || !form.date) {
      toast.error("Pick a bank account and a date.");
      return;
    }
    setBusy(true);
    try {
      await accountingApi.bankStatementLines.create({
        bank_account: bankId,
        date: form.date,
        description: form.description,
        reference: form.reference,
        amount: form.amount || "0",
      });
      toast.success("Statement line added.");
      setOpen(false);
      setForm(emptyStatement);
      await load();
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const remove = async (l: BankStatementLine) => {
    const yes = await confirm({
      title: "Delete statement line",
      message: "Delete this statement line?",
      danger: true,
      confirmText: "Delete",
    });
    if (yes) await act(() => accountingApi.bankStatementLines.remove(l.id), "Statement line deleted.");
  };

  const importCsv = async () => {
    if (!bankId || !csvText.trim()) {
      toast.error("Paste CSV rows to import.");
      return;
    }
    setImporting(true);
    try {
      const res = await accountingApi.bankStatementLines.importCsv(bankId, csvText);
      toast.success(`Imported ${res.imported} statement line(s).`);
      setImportOpen(false);
      setCsvText("");
      await load();
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setImporting(false);
    }
  };

  const autoMatch = async () => {
    if (!bankId) return;
    setMatching(true);
    try {
      const res = await accountingApi.bankAccounts.autoMatch(bankId);
      toast.success(
        res.matched > 0
          ? `Auto-matched ${res.matched} statement line(s).`
          : "No new matches found.",
      );
      await load();
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setMatching(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-2">
        <div className="min-w-[220px] flex-1">
          <Select
            label="Bank account"
            value={bankId}
            onChange={(e) => setBankId(e.target.value)}
            placeholder="Select bank account"
          >
            {banks.map((b) => (
              <option key={b.id} value={b.id}>
                {b.name}
              </option>
            ))}
          </Select>
        </div>
        <Button variant="secondary" disabled={!bankId} onClick={() => setImportOpen(true)}>
          <Upload className="h-4 w-4" /> Import CSV
        </Button>
        <Button
          variant="secondary"
          disabled={!bankId || matching || lines.length === 0}
          loading={matching}
          onClick={autoMatch}
        >
          <Wand2 className="h-4 w-4" /> Auto-match
        </Button>
        <Button disabled={!bankId} onClick={() => setOpen(true)}>
          <Plus className="h-4 w-4" /> Add statement line
        </Button>
      </div>

      {!bankId ? (
        <EmptyState title="Select a bank account" description="Pick a bank account to reconcile its statement lines." />
      ) : loading ? (
        <div className="text-sm text-[var(--muted)]">Loading…</div>
      ) : lines.length === 0 ? (
        <EmptyState title="No statement lines" description="Add statement lines to begin reconciliation." />
      ) : (
        <Table>
          <thead>
            <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
              <th className="px-4 py-3 font-medium">Date</th>
              <th className="px-4 py-3 font-medium">Description</th>
              <th className="px-4 py-3 font-medium">Reference</th>
              <th className="px-4 py-3 font-medium text-right">Amount</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {lines.map((l) => (
              <tr key={l.id} className="border-b border-[var(--border)] last:border-0">
                <td className="px-4 py-3 text-[var(--foreground-secondary)]">{l.date}</td>
                <td className="px-4 py-3 text-[var(--foreground)]">{l.description || "—"}</td>
                <td className="px-4 py-3 text-[var(--foreground-secondary)]">{l.reference || "—"}</td>
                <td className="px-4 py-3 text-right font-semibold text-[var(--foreground)]">
                  {formatMoney(l.amount)}
                </td>
                <td className="px-4 py-3">
                  <StatusBadge
                    status={l.is_reconciled ? "reconciled" : "pending"}
                    label={l.is_reconciled ? "Reconciled" : "Unreconciled"}
                  />
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center justify-end gap-1">
                    {l.is_reconciled ? (
                      <Button
                        variant="ghost"
                        size="sm"
                        title="Unreconcile"
                        onClick={() => act(() => accountingApi.bankStatementLines.unreconcile(l.id), "Line unreconciled.")}
                      >
                        <RotateCcw className="h-4 w-4 text-[var(--warning)]" />
                      </Button>
                    ) : (
                      <Button
                        variant="ghost"
                        size="sm"
                        title="Reconcile"
                        onClick={() => act(() => accountingApi.bankStatementLines.reconcile(l.id), "Line reconciled.")}
                      >
                        <CheckCircle2 className="h-4 w-4 text-[var(--success)]" />
                      </Button>
                    )}
                    <Button variant="ghost" size="sm" title="Delete" onClick={() => remove(l)}>
                      <Trash2 className="h-4 w-4 text-[var(--error)]" />
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      <Modal open={open} title="Add statement line" onClose={() => setOpen(false)}>
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <Input label="Date" type="date" value={form.date} onChange={(e) => set({ date: e.target.value })} />
            <Input label="Amount" type="number" value={form.amount} onChange={(e) => set({ amount: e.target.value })} />
          </div>
          <Input label="Description" value={form.description} onChange={(e) => set({ description: e.target.value })} />
          <Input label="Reference" value={form.reference} onChange={(e) => set({ reference: e.target.value })} />
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button loading={busy} onClick={addLine}>
              Add line
            </Button>
          </div>
        </div>
      </Modal>

      <Modal open={importOpen} title="Import bank statement (CSV)" onClose={() => setImportOpen(false)}>
        <div className="space-y-3">
          <p className="text-[11px] text-[var(--muted)]">
            Paste CSV rows with columns <code>date, description, reference, amount</code> (a header
            row is optional). Positive amounts are money in, negative amounts money out.
          </p>
          <Textarea
            label="CSV content"
            rows={8}
            value={csvText}
            onChange={(e) => setCsvText(e.target.value)}
            placeholder={"date,description,reference,amount\n2026-07-01,Deposit,REF001,500.00\n2026-07-02,Utility,REF002,-120.00"}
          />
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setImportOpen(false)}>
              Cancel
            </Button>
            <Button loading={importing} onClick={importCsv}>
              <Upload className="h-4 w-4" /> Import
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
