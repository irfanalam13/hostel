"use client";

import React, { useCallback, useEffect, useState } from "react";
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
import { History, Pencil, Plus, TrendingDown, Trash2, XOctagon } from "lucide-react";

import { accountingApi } from "../api/accounting.api";
import type {
  Account,
  AssetDepreciation,
  DepreciationMethod,
  FixedAsset,
  FixedAssetPayload,
} from "../types/accounting.types";
import { DEPRECIATION_METHODS, StatusBadge, formatMoney } from "./primitives";

const STATUS_FILTERS = [
  { value: "", label: "All statuses" },
  { value: "active", label: "Active" },
  { value: "disposed", label: "Disposed" },
  { value: "fully_depreciated", label: "Fully Depreciated" },
];

type AssetForm = {
  name: string;
  category: string;
  code: string;
  purchase_cost: string;
  purchase_date: string;
  useful_life_months: string;
  salvage_value: string;
  depreciation_method: DepreciationMethod;
  declining_rate: string;
  asset_account: string;
  depreciation_expense_account: string;
  accumulated_depreciation_account: string;
};

const emptyAsset: AssetForm = {
  name: "",
  category: "",
  code: "",
  purchase_cost: "0",
  purchase_date: "",
  useful_life_months: "60",
  salvage_value: "0",
  depreciation_method: "straight_line",
  declining_rate: "0",
  asset_account: "",
  depreciation_expense_account: "",
  accumulated_depreciation_account: "",
};

export function FixedAssets() {
  const toast = useToast();
  const confirm = useConfirm();

  const [rows, setRows] = useState<FixedAsset[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");

  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<FixedAsset | null>(null);
  const [form, setForm] = useState<AssetForm>(emptyAsset);
  const [busy, setBusy] = useState(false);

  const [historyFor, setHistoryFor] = useState<FixedAsset | null>(null);
  const [history, setHistory] = useState<AssetDepreciation[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows(await accountingApi.fixedAssets.list({ status: statusFilter || undefined }));
    } catch (e) {
      toast.error((e as Error).message, "Couldn't load assets");
    } finally {
      setLoading(false);
    }
  }, [statusFilter, toast]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    accountingApi.accounts
      .list({ is_group: "false", ordering: "code" })
      .then(setAccounts)
      .catch(() => {});
  }, []);

  const set = (patch: Partial<AssetForm>) => setForm((f) => ({ ...f, ...patch }));

  const startCreate = () => {
    setEditing(null);
    setForm(emptyAsset);
    setOpen(true);
  };
  const startEdit = (a: FixedAsset) => {
    setEditing(a);
    setForm({
      name: a.name,
      category: a.category,
      code: a.code,
      purchase_cost: a.purchase_cost,
      purchase_date: a.purchase_date,
      useful_life_months: String(a.useful_life_months),
      salvage_value: a.salvage_value,
      depreciation_method: a.depreciation_method,
      declining_rate: a.declining_rate,
      asset_account: a.asset_account ?? "",
      depreciation_expense_account: a.depreciation_expense_account ?? "",
      accumulated_depreciation_account: a.accumulated_depreciation_account ?? "",
    });
    setOpen(true);
  };

  const submit = async () => {
    if (!form.name.trim() || !form.purchase_date) {
      toast.error("Name and purchase date are required.");
      return;
    }
    setBusy(true);
    try {
      const body: FixedAssetPayload = {
        name: form.name.trim(),
        category: form.category,
        code: form.code || undefined,
        purchase_cost: form.purchase_cost || "0",
        purchase_date: form.purchase_date,
        useful_life_months: Number(form.useful_life_months) || 0,
        salvage_value: form.salvage_value || "0",
        depreciation_method: form.depreciation_method,
        declining_rate: form.declining_rate || "0",
        asset_account: form.asset_account || null,
        depreciation_expense_account: form.depreciation_expense_account || null,
        accumulated_depreciation_account: form.accumulated_depreciation_account || null,
      };
      if (editing) await accountingApi.fixedAssets.update(editing.id, body);
      else await accountingApi.fixedAssets.create(body);
      toast.success(editing ? "Asset updated." : "Asset created.");
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

  const dispose = async (a: FixedAsset) => {
    const yes = await confirm({
      title: "Dispose asset",
      message: `Dispose "${a.name}"? This posts a disposal entry.`,
      danger: true,
      confirmText: "Dispose",
    });
    if (yes) await act(() => accountingApi.fixedAssets.dispose(a.id), "Asset disposed.");
  };

  const remove = async (a: FixedAsset) => {
    const yes = await confirm({
      title: "Delete asset",
      message: `Delete "${a.name}"?`,
      danger: true,
      confirmText: "Delete",
    });
    if (yes) await act(() => accountingApi.fixedAssets.remove(a.id), "Asset deleted.");
  };

  const openHistory = async (a: FixedAsset) => {
    setHistoryFor(a);
    setHistory([]);
    setHistoryLoading(true);
    try {
      setHistory(await accountingApi.fixedAssets.depreciations(a.id));
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setHistoryLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-2">
        <Select
          label="Status"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          options={STATUS_FILTERS}
        />
        <div className="flex-1" />
        <Button onClick={startCreate}>
          <Plus className="h-4 w-4" /> New asset
        </Button>
      </div>

      {loading ? (
        <div className="text-sm text-[var(--muted)]">Loading…</div>
      ) : rows.length === 0 ? (
        <EmptyState title="No fixed assets" description="Register assets to track depreciation and disposal." />
      ) : (
        <Table>
          <thead>
            <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
              <th className="px-4 py-3 font-medium">Name</th>
              <th className="px-4 py-3 font-medium">Category</th>
              <th className="px-4 py-3 font-medium text-right">Cost</th>
              <th className="px-4 py-3 font-medium text-right">Accum. Deprec.</th>
              <th className="px-4 py-3 font-medium text-right">NBV</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((a) => (
              <tr key={a.id} className="border-b border-[var(--border)] last:border-0">
                <td className="px-4 py-3">
                  <div className="font-medium text-[var(--foreground)]">{a.name}</div>
                  {a.code ? <div className="text-xs text-[var(--muted)]">{a.code}</div> : null}
                </td>
                <td className="px-4 py-3 text-[var(--foreground-secondary)]">{a.category || "—"}</td>
                <td className="px-4 py-3 text-right text-[var(--foreground-secondary)]">
                  {formatMoney(a.purchase_cost)}
                </td>
                <td className="px-4 py-3 text-right text-[var(--foreground-secondary)]">
                  {formatMoney(a.accumulated_depreciation)}
                </td>
                <td className="px-4 py-3 text-right font-semibold text-[var(--foreground)]">
                  {formatMoney(a.net_book_value)}
                </td>
                <td className="px-4 py-3">
                  <StatusBadge status={a.status} />
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center justify-end gap-1">
                    <Button variant="ghost" size="sm" title="Depreciation history" onClick={() => openHistory(a)}>
                      <History className="h-4 w-4" />
                    </Button>
                    {a.status === "active" ? (
                      <>
                        <Button
                          variant="ghost"
                          size="sm"
                          title="Depreciate"
                          onClick={() => act(() => accountingApi.fixedAssets.depreciate(a.id), "Depreciation posted.")}
                        >
                          <TrendingDown className="h-4 w-4 text-[var(--warning)]" />
                        </Button>
                        <Button variant="ghost" size="sm" title="Dispose" onClick={() => dispose(a)}>
                          <XOctagon className="h-4 w-4 text-[var(--error)]" />
                        </Button>
                      </>
                    ) : null}
                    <Button variant="ghost" size="sm" title="Edit" onClick={() => startEdit(a)}>
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="sm" title="Delete" onClick={() => remove(a)}>
                      <Trash2 className="h-4 w-4 text-[var(--error)]" />
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      {/* Create / edit */}
      <Modal open={open} title={editing ? "Edit asset" : "New asset"} onClose={() => setOpen(false)}>
        <div className="max-h-[74vh] space-y-3 overflow-y-auto pr-1">
          <div className="grid grid-cols-2 gap-3">
            <Input label="Name" value={form.name} onChange={(e) => set({ name: e.target.value })} />
            <Input label="Category" value={form.category} onChange={(e) => set({ category: e.target.value })} />
          </div>
          <div className="grid grid-cols-3 gap-3">
            <Input label="Code (optional)" value={form.code} onChange={(e) => set({ code: e.target.value })} />
            <Input
              label="Purchase cost"
              type="number"
              value={form.purchase_cost}
              onChange={(e) => set({ purchase_cost: e.target.value })}
            />
            <Input
              label="Purchase date"
              type="date"
              value={form.purchase_date}
              onChange={(e) => set({ purchase_date: e.target.value })}
            />
          </div>
          <div className="grid grid-cols-3 gap-3">
            <Input
              label="Useful life (months)"
              type="number"
              value={form.useful_life_months}
              onChange={(e) => set({ useful_life_months: e.target.value })}
            />
            <Input
              label="Salvage value"
              type="number"
              value={form.salvage_value}
              onChange={(e) => set({ salvage_value: e.target.value })}
            />
            <Input
              label="Declining rate %"
              type="number"
              value={form.declining_rate}
              onChange={(e) => set({ declining_rate: e.target.value })}
            />
          </div>
          <Select
            label="Depreciation method"
            value={form.depreciation_method}
            onChange={(e) => set({ depreciation_method: e.target.value as DepreciationMethod })}
            options={DEPRECIATION_METHODS}
          />
          <Select
            label="Asset account"
            value={form.asset_account}
            onChange={(e) => set({ asset_account: e.target.value })}
            placeholder="Select account"
          >
            {accounts.map((a) => (
              <option key={a.id} value={a.id}>
                {a.code} · {a.name}
              </option>
            ))}
          </Select>
          <Select
            label="Depreciation expense account"
            value={form.depreciation_expense_account}
            onChange={(e) => set({ depreciation_expense_account: e.target.value })}
            placeholder="Select account"
          >
            {accounts.map((a) => (
              <option key={a.id} value={a.id}>
                {a.code} · {a.name}
              </option>
            ))}
          </Select>
          <Select
            label="Accumulated depreciation account"
            value={form.accumulated_depreciation_account}
            onChange={(e) => set({ accumulated_depreciation_account: e.target.value })}
            placeholder="Select account"
          >
            {accounts.map((a) => (
              <option key={a.id} value={a.id}>
                {a.code} · {a.name}
              </option>
            ))}
          </Select>
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

      {/* Depreciation history */}
      <Modal
        open={!!historyFor}
        title={historyFor ? `Depreciation · ${historyFor.name}` : "Depreciation"}
        onClose={() => setHistoryFor(null)}
      >
        <div className="max-h-[74vh] space-y-2 overflow-y-auto pr-1">
          {historyLoading ? (
            <div className="text-sm text-[var(--muted)]">Loading…</div>
          ) : history.length === 0 ? (
            <p className="py-4 text-center text-sm text-[var(--muted)]">No depreciation posted yet.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-[var(--border)] text-[var(--muted)]">
                    <th className="py-2 pr-3 font-medium">Date</th>
                    <th className="py-2 pr-3 font-medium text-right">Amount</th>
                    <th className="py-2 pr-3 font-medium text-right">Accumulated</th>
                    <th className="py-2 font-medium text-right">NBV</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border)]">
                  {history.map((d) => (
                    <tr key={d.id}>
                      <td className="py-2 pr-3 text-[var(--foreground-secondary)]">{d.date}</td>
                      <td className="py-2 pr-3 text-right text-[var(--foreground)]">{formatMoney(d.amount)}</td>
                      <td className="py-2 pr-3 text-right text-[var(--foreground-secondary)]">
                        {formatMoney(d.accumulated_depreciation)}
                      </td>
                      <td className="py-2 text-right text-[var(--foreground-secondary)]">
                        {formatMoney(d.net_book_value)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </Modal>
    </div>
  );
}
