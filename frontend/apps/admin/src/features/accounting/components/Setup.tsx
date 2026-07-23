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
import { Pencil, Plus, Trash2 } from "lucide-react";

import { accountingApi } from "../api/accounting.api";
import type {
  Account,
  Branch,
  CostCenter,
  Currency,
  ExchangeRate,
  TaxCode,
  TaxType,
} from "../types/accounting.types";
import { StatusBadge, TAX_TYPES } from "./primitives";

const TABS = [
  { id: "cost_centers", label: "Cost Centers" },
  { id: "branches", label: "Branches" },
  { id: "currencies", label: "Currencies" },
  { id: "exchange_rates", label: "Exchange Rates" },
  { id: "tax_codes", label: "Tax Codes" },
] as const;
type TabId = (typeof TABS)[number]["id"];

export function Setup() {
  const [tab, setTab] = useState<TabId>("cost_centers");

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

      {tab === "cost_centers" && <CostCentersTab />}
      {tab === "branches" && <BranchesTab />}
      {tab === "currencies" && <CurrenciesTab />}
      {tab === "exchange_rates" && <ExchangeRatesTab />}
      {tab === "tax_codes" && <TaxCodesTab />}
    </div>
  );
}

function ActiveCell({ active }: { active: boolean }) {
  return (
    <StatusBadge status={active ? "active" : "inactive"} label={active ? "Active" : "Inactive"} />
  );
}

/* ----------------------------- Cost centers ------------------------------ */

type CostCenterForm = { name: string; code: string; description: string; is_active: boolean };
const emptyCostCenter: CostCenterForm = { name: "", code: "", description: "", is_active: true };

function CostCentersTab() {
  const toast = useToast();
  const confirm = useConfirm();
  const [rows, setRows] = useState<CostCenter[]>([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<CostCenter | null>(null);
  const [form, setForm] = useState<CostCenterForm>(emptyCostCenter);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows(await accountingApi.costCenters.list());
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    load();
  }, [load]);

  const set = (patch: Partial<CostCenterForm>) => setForm((f) => ({ ...f, ...patch }));
  const startCreate = () => {
    setEditing(null);
    setForm(emptyCostCenter);
    setOpen(true);
  };
  const startEdit = (c: CostCenter) => {
    setEditing(c);
    setForm({ name: c.name, code: c.code, description: c.description, is_active: c.is_active });
    setOpen(true);
  };

  const submit = async () => {
    if (!form.name.trim()) {
      toast.error("A name is required.");
      return;
    }
    setBusy(true);
    try {
      if (editing) await accountingApi.costCenters.update(editing.id, form);
      else await accountingApi.costCenters.create(form);
      toast.success(editing ? "Cost center updated." : "Cost center created.");
      setOpen(false);
      await load();
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const remove = async (c: CostCenter) => {
    const yes = await confirm({ title: "Delete cost center", message: `Delete "${c.name}"?`, danger: true, confirmText: "Delete" });
    if (!yes) return;
    try {
      await accountingApi.costCenters.remove(c.id);
      toast.success("Cost center deleted.");
      await load();
    } catch (e) {
      toast.error((e as Error).message);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button onClick={startCreate}>
          <Plus className="h-4 w-4" /> New cost center
        </Button>
      </div>
      {loading ? (
        <div className="text-sm text-[var(--muted)]">Loading…</div>
      ) : rows.length === 0 ? (
        <EmptyState title="No cost centers" description="Track spending against cost centers." />
      ) : (
        <Table>
          <thead>
            <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
              <th className="px-4 py-3 font-medium">Name</th>
              <th className="px-4 py-3 font-medium">Code</th>
              <th className="px-4 py-3 font-medium">Active</th>
              <th className="px-4 py-3 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((c) => (
              <tr key={c.id} className="border-b border-[var(--border)] last:border-0">
                <td className="px-4 py-3">
                  <div className="font-medium text-[var(--foreground)]">{c.name}</div>
                  {c.description ? <div className="text-xs text-[var(--muted)]">{c.description}</div> : null}
                </td>
                <td className="px-4 py-3 text-[var(--foreground-secondary)]">{c.code || "—"}</td>
                <td className="px-4 py-3">
                  <ActiveCell active={c.is_active} />
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center justify-end gap-1">
                    <Button variant="ghost" size="sm" title="Edit" onClick={() => startEdit(c)}>
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="sm" title="Delete" onClick={() => remove(c)}>
                      <Trash2 className="h-4 w-4 text-[var(--error)]" />
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
      <Modal open={open} title={editing ? "Edit cost center" : "New cost center"} onClose={() => setOpen(false)}>
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <Input label="Name" value={form.name} onChange={(e) => set({ name: e.target.value })} />
            <Input label="Code" value={form.code} onChange={(e) => set({ code: e.target.value })} />
          </div>
          <Textarea label="Description" value={form.description} onChange={(e) => set({ description: e.target.value })} />
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

/* ------------------------------- Branches -------------------------------- */

type BranchForm = { name: string; code: string; is_active: boolean };
const emptyBranch: BranchForm = { name: "", code: "", is_active: true };

function BranchesTab() {
  const toast = useToast();
  const confirm = useConfirm();
  const [rows, setRows] = useState<Branch[]>([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Branch | null>(null);
  const [form, setForm] = useState<BranchForm>(emptyBranch);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows(await accountingApi.branches.list());
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    load();
  }, [load]);

  const set = (patch: Partial<BranchForm>) => setForm((f) => ({ ...f, ...patch }));
  const startCreate = () => {
    setEditing(null);
    setForm(emptyBranch);
    setOpen(true);
  };
  const startEdit = (b: Branch) => {
    setEditing(b);
    setForm({ name: b.name, code: b.code, is_active: b.is_active });
    setOpen(true);
  };

  const submit = async () => {
    if (!form.name.trim()) {
      toast.error("A name is required.");
      return;
    }
    setBusy(true);
    try {
      if (editing) await accountingApi.branches.update(editing.id, form);
      else await accountingApi.branches.create(form);
      toast.success(editing ? "Branch updated." : "Branch created.");
      setOpen(false);
      await load();
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const remove = async (b: Branch) => {
    const yes = await confirm({ title: "Delete branch", message: `Delete "${b.name}"?`, danger: true, confirmText: "Delete" });
    if (!yes) return;
    try {
      await accountingApi.branches.remove(b.id);
      toast.success("Branch deleted.");
      await load();
    } catch (e) {
      toast.error((e as Error).message);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button onClick={startCreate}>
          <Plus className="h-4 w-4" /> New branch
        </Button>
      </div>
      {loading ? (
        <div className="text-sm text-[var(--muted)]">Loading…</div>
      ) : rows.length === 0 ? (
        <EmptyState title="No branches" description="Add branches for multi-location accounting." />
      ) : (
        <Table>
          <thead>
            <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
              <th className="px-4 py-3 font-medium">Name</th>
              <th className="px-4 py-3 font-medium">Code</th>
              <th className="px-4 py-3 font-medium">Active</th>
              <th className="px-4 py-3 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((b) => (
              <tr key={b.id} className="border-b border-[var(--border)] last:border-0">
                <td className="px-4 py-3 font-medium text-[var(--foreground)]">{b.name}</td>
                <td className="px-4 py-3 text-[var(--foreground-secondary)]">{b.code || "—"}</td>
                <td className="px-4 py-3">
                  <ActiveCell active={b.is_active} />
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
      <Modal open={open} title={editing ? "Edit branch" : "New branch"} onClose={() => setOpen(false)}>
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <Input label="Name" value={form.name} onChange={(e) => set({ name: e.target.value })} />
            <Input label="Code" value={form.code} onChange={(e) => set({ code: e.target.value })} />
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

/* ------------------------------ Currencies ------------------------------- */

type CurrencyForm = { code: string; name: string; symbol: string; is_base: boolean; is_active: boolean };
const emptyCurrency: CurrencyForm = { code: "", name: "", symbol: "", is_base: false, is_active: true };

function CurrenciesTab() {
  const toast = useToast();
  const confirm = useConfirm();
  const [rows, setRows] = useState<Currency[]>([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Currency | null>(null);
  const [form, setForm] = useState<CurrencyForm>(emptyCurrency);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows(await accountingApi.currencies.list());
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    load();
  }, [load]);

  const set = (patch: Partial<CurrencyForm>) => setForm((f) => ({ ...f, ...patch }));
  const startCreate = () => {
    setEditing(null);
    setForm(emptyCurrency);
    setOpen(true);
  };
  const startEdit = (c: Currency) => {
    setEditing(c);
    setForm({ code: c.code, name: c.name, symbol: c.symbol, is_base: c.is_base, is_active: c.is_active });
    setOpen(true);
  };

  const submit = async () => {
    if (!form.code.trim() || !form.name.trim()) {
      toast.error("Code and name are required.");
      return;
    }
    setBusy(true);
    try {
      if (editing) await accountingApi.currencies.update(editing.id, form);
      else await accountingApi.currencies.create(form);
      toast.success(editing ? "Currency updated." : "Currency created.");
      setOpen(false);
      await load();
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const remove = async (c: Currency) => {
    const yes = await confirm({ title: "Delete currency", message: `Delete "${c.code}"?`, danger: true, confirmText: "Delete" });
    if (!yes) return;
    try {
      await accountingApi.currencies.remove(c.id);
      toast.success("Currency deleted.");
      await load();
    } catch (e) {
      toast.error((e as Error).message);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button onClick={startCreate}>
          <Plus className="h-4 w-4" /> New currency
        </Button>
      </div>
      {loading ? (
        <div className="text-sm text-[var(--muted)]">Loading…</div>
      ) : rows.length === 0 ? (
        <EmptyState title="No currencies" description="Add currencies used across your books." />
      ) : (
        <Table>
          <thead>
            <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
              <th className="px-4 py-3 font-medium">Code</th>
              <th className="px-4 py-3 font-medium">Name</th>
              <th className="px-4 py-3 font-medium">Symbol</th>
              <th className="px-4 py-3 font-medium">Base</th>
              <th className="px-4 py-3 font-medium">Active</th>
              <th className="px-4 py-3 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((c) => (
              <tr key={c.id} className="border-b border-[var(--border)] last:border-0">
                <td className="px-4 py-3 font-medium text-[var(--foreground)]">{c.code}</td>
                <td className="px-4 py-3 text-[var(--foreground-secondary)]">{c.name}</td>
                <td className="px-4 py-3 text-[var(--foreground-secondary)]">{c.symbol || "—"}</td>
                <td className="px-4 py-3">
                  {c.is_base ? <StatusBadge status="active" label="Base" /> : <span className="text-[var(--muted)]">—</span>}
                </td>
                <td className="px-4 py-3">
                  <ActiveCell active={c.is_active} />
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center justify-end gap-1">
                    <Button variant="ghost" size="sm" title="Edit" onClick={() => startEdit(c)}>
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="sm" title="Delete" onClick={() => remove(c)}>
                      <Trash2 className="h-4 w-4 text-[var(--error)]" />
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
      <Modal open={open} title={editing ? "Edit currency" : "New currency"} onClose={() => setOpen(false)}>
        <div className="space-y-3">
          <div className="grid grid-cols-3 gap-3">
            <Input label="Code" value={form.code} onChange={(e) => set({ code: e.target.value })} />
            <Input label="Name" value={form.name} onChange={(e) => set({ name: e.target.value })} />
            <Input label="Symbol" value={form.symbol} onChange={(e) => set({ symbol: e.target.value })} />
          </div>
          <div className="flex flex-wrap gap-4">
            <label className="flex items-center gap-2 text-sm text-[var(--foreground-secondary)]">
              <input type="checkbox" checked={form.is_base} onChange={(e) => set({ is_base: e.target.checked })} />
              Base currency
            </label>
            <label className="flex items-center gap-2 text-sm text-[var(--foreground-secondary)]">
              <input type="checkbox" checked={form.is_active} onChange={(e) => set({ is_active: e.target.checked })} />
              Active
            </label>
          </div>
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

/* ---------------------------- Exchange rates ----------------------------- */

type RateForm = { currency: string; rate_to_base: string; as_of: string };
const emptyRate: RateForm = { currency: "", rate_to_base: "1", as_of: "" };

function ExchangeRatesTab() {
  const toast = useToast();
  const confirm = useConfirm();
  const [rows, setRows] = useState<ExchangeRate[]>([]);
  const [currencies, setCurrencies] = useState<Currency[]>([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<ExchangeRate | null>(null);
  const [form, setForm] = useState<RateForm>(emptyRate);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows(await accountingApi.exchangeRates.list());
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    load();
    accountingApi.currencies.list().then(setCurrencies).catch(() => {});
  }, [load]);

  const set = (patch: Partial<RateForm>) => setForm((f) => ({ ...f, ...patch }));
  const startCreate = () => {
    setEditing(null);
    setForm({ ...emptyRate, currency: currencies[0]?.id ?? "" });
    setOpen(true);
  };
  const startEdit = (r: ExchangeRate) => {
    setEditing(r);
    setForm({ currency: r.currency, rate_to_base: r.rate_to_base, as_of: r.as_of });
    setOpen(true);
  };

  const submit = async () => {
    if (!form.currency || !form.as_of) {
      toast.error("Currency and date are required.");
      return;
    }
    setBusy(true);
    try {
      if (editing) await accountingApi.exchangeRates.update(editing.id, form);
      else await accountingApi.exchangeRates.create(form);
      toast.success(editing ? "Rate updated." : "Rate created.");
      setOpen(false);
      await load();
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const remove = async (r: ExchangeRate) => {
    const yes = await confirm({ title: "Delete rate", message: `Delete the ${r.currency_code} rate?`, danger: true, confirmText: "Delete" });
    if (!yes) return;
    try {
      await accountingApi.exchangeRates.remove(r.id);
      toast.success("Rate deleted.");
      await load();
    } catch (e) {
      toast.error((e as Error).message);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button onClick={startCreate}>
          <Plus className="h-4 w-4" /> New rate
        </Button>
      </div>
      {loading ? (
        <div className="text-sm text-[var(--muted)]">Loading…</div>
      ) : rows.length === 0 ? (
        <EmptyState title="No exchange rates" description="Record exchange rates to the base currency." />
      ) : (
        <Table>
          <thead>
            <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
              <th className="px-4 py-3 font-medium">Currency</th>
              <th className="px-4 py-3 font-medium text-right">Rate to base</th>
              <th className="px-4 py-3 font-medium">As of</th>
              <th className="px-4 py-3 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} className="border-b border-[var(--border)] last:border-0">
                <td className="px-4 py-3 font-medium text-[var(--foreground)]">{r.currency_code}</td>
                <td className="px-4 py-3 text-right text-[var(--foreground-secondary)]">{r.rate_to_base}</td>
                <td className="px-4 py-3 text-[var(--foreground-secondary)]">{r.as_of}</td>
                <td className="px-4 py-3">
                  <div className="flex items-center justify-end gap-1">
                    <Button variant="ghost" size="sm" title="Edit" onClick={() => startEdit(r)}>
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="sm" title="Delete" onClick={() => remove(r)}>
                      <Trash2 className="h-4 w-4 text-[var(--error)]" />
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
      <Modal open={open} title={editing ? "Edit rate" : "New rate"} onClose={() => setOpen(false)}>
        <div className="space-y-3">
          <Select
            label="Currency"
            value={form.currency}
            onChange={(e) => set({ currency: e.target.value })}
            placeholder="Select currency"
          >
            {currencies.map((c) => (
              <option key={c.id} value={c.id}>
                {c.code} · {c.name}
              </option>
            ))}
          </Select>
          <div className="grid grid-cols-2 gap-3">
            <Input
              label="Rate to base"
              type="number"
              value={form.rate_to_base}
              onChange={(e) => set({ rate_to_base: e.target.value })}
            />
            <Input label="As of" type="date" value={form.as_of} onChange={(e) => set({ as_of: e.target.value })} />
          </div>
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

/* ------------------------------- Tax codes ------------------------------- */

type TaxForm = {
  name: string;
  tax_type: TaxType;
  rate: string;
  payable_account: string;
  receivable_account: string;
  is_active: boolean;
};
const emptyTax: TaxForm = {
  name: "",
  tax_type: "vat",
  rate: "0",
  payable_account: "",
  receivable_account: "",
  is_active: true,
};

function TaxCodesTab() {
  const toast = useToast();
  const confirm = useConfirm();
  const [rows, setRows] = useState<TaxCode[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<TaxCode | null>(null);
  const [form, setForm] = useState<TaxForm>(emptyTax);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows(await accountingApi.taxCodes.list());
    } catch (e) {
      toast.error((e as Error).message);
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
  }, [load]);

  const set = (patch: Partial<TaxForm>) => setForm((f) => ({ ...f, ...patch }));
  const startCreate = () => {
    setEditing(null);
    setForm(emptyTax);
    setOpen(true);
  };
  const startEdit = (t: TaxCode) => {
    setEditing(t);
    setForm({
      name: t.name,
      tax_type: t.tax_type,
      rate: t.rate,
      payable_account: t.payable_account ?? "",
      receivable_account: t.receivable_account ?? "",
      is_active: t.is_active,
    });
    setOpen(true);
  };

  const submit = async () => {
    if (!form.name.trim()) {
      toast.error("A name is required.");
      return;
    }
    setBusy(true);
    try {
      const body: Partial<TaxCode> = {
        name: form.name.trim(),
        tax_type: form.tax_type,
        rate: form.rate || "0",
        payable_account: form.payable_account || null,
        receivable_account: form.receivable_account || null,
        is_active: form.is_active,
      };
      if (editing) await accountingApi.taxCodes.update(editing.id, body);
      else await accountingApi.taxCodes.create(body);
      toast.success(editing ? "Tax code updated." : "Tax code created.");
      setOpen(false);
      await load();
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const remove = async (t: TaxCode) => {
    const yes = await confirm({ title: "Delete tax code", message: `Delete "${t.name}"?`, danger: true, confirmText: "Delete" });
    if (!yes) return;
    try {
      await accountingApi.taxCodes.remove(t.id);
      toast.success("Tax code deleted.");
      await load();
    } catch (e) {
      toast.error((e as Error).message);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button onClick={startCreate}>
          <Plus className="h-4 w-4" /> New tax code
        </Button>
      </div>
      {loading ? (
        <div className="text-sm text-[var(--muted)]">Loading…</div>
      ) : rows.length === 0 ? (
        <EmptyState title="No tax codes" description="Define tax codes for tax-aware postings." />
      ) : (
        <Table>
          <thead>
            <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
              <th className="px-4 py-3 font-medium">Name</th>
              <th className="px-4 py-3 font-medium">Type</th>
              <th className="px-4 py-3 font-medium text-right">Rate %</th>
              <th className="px-4 py-3 font-medium">Active</th>
              <th className="px-4 py-3 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((t) => (
              <tr key={t.id} className="border-b border-[var(--border)] last:border-0">
                <td className="px-4 py-3 font-medium text-[var(--foreground)]">{t.name}</td>
                <td className="px-4 py-3 uppercase text-[var(--foreground-secondary)]">{t.tax_type}</td>
                <td className="px-4 py-3 text-right text-[var(--foreground-secondary)]">{t.rate}</td>
                <td className="px-4 py-3">
                  <ActiveCell active={t.is_active} />
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center justify-end gap-1">
                    <Button variant="ghost" size="sm" title="Edit" onClick={() => startEdit(t)}>
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="sm" title="Delete" onClick={() => remove(t)}>
                      <Trash2 className="h-4 w-4 text-[var(--error)]" />
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
      <Modal open={open} title={editing ? "Edit tax code" : "New tax code"} onClose={() => setOpen(false)}>
        <div className="max-h-[74vh] space-y-3 overflow-y-auto pr-1">
          <div className="grid grid-cols-3 gap-3">
            <Input label="Name" value={form.name} onChange={(e) => set({ name: e.target.value })} />
            <Select label="Type" value={form.tax_type} onChange={(e) => set({ tax_type: e.target.value as TaxType })} options={TAX_TYPES} />
            <Input label="Rate %" type="number" value={form.rate} onChange={(e) => set({ rate: e.target.value })} />
          </div>
          <Select
            label="Payable account (optional)"
            value={form.payable_account}
            onChange={(e) => set({ payable_account: e.target.value })}
            placeholder="No account"
          >
            {accounts.map((a) => (
              <option key={a.id} value={a.id}>
                {a.code} · {a.name}
              </option>
            ))}
          </Select>
          <Select
            label="Receivable account (optional)"
            value={form.receivable_account}
            onChange={(e) => set({ receivable_account: e.target.value })}
            placeholder="No account"
          >
            {accounts.map((a) => (
              <option key={a.id} value={a.id}>
                {a.code} · {a.name}
              </option>
            ))}
          </Select>
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
