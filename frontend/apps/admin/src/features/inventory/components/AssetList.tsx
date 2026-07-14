"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Button, EmptyState, Input, Modal, Select, Table, useToast } from "@hostel/ui";
import { Eye, Plus } from "lucide-react";

import { inventoryApi } from "../api/inventory.api";
import { ASSET_CONDITIONS, ASSET_STATUSES, DEPRECIATION_METHODS } from "../constants";
import type { Asset, ItemCategory, Vendor } from "../types/inventory.types";
import { StatusBadge, formatMoney } from "./primitives";

type AssetForm = {
  name: string;
  category: string;
  vendor: string;
  serial_number: string;
  purchase_date: string;
  purchase_cost: string;
  condition: Asset["condition"];
  useful_life_months: string;
  salvage_value: string;
  depreciation_method: string;
  department: string;
};

const empty: AssetForm = {
  name: "",
  category: "",
  vendor: "",
  serial_number: "",
  purchase_date: "",
  purchase_cost: "0",
  condition: "good",
  useful_life_months: "0",
  salvage_value: "0",
  depreciation_method: "none",
  department: "",
};

export function AssetList() {
  const toast = useToast();

  const [rows, setRows] = useState<Asset[]>([]);
  const [categories, setCategories] = useState<ItemCategory[]>([]);
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  const [open, setOpen] = useState(false);
  const [form, setForm] = useState<AssetForm>(empty);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows(await inventoryApi.assets.list({ search, status: statusFilter || undefined }));
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [search, statusFilter, toast]);

  useEffect(() => {
    const t = setTimeout(load, 200);
    return () => clearTimeout(t);
  }, [load]);

  useEffect(() => {
    inventoryApi.categories.list().then(setCategories).catch(() => {});
    inventoryApi.vendors.list().then(setVendors).catch(() => {});
  }, []);

  const set = (patch: Partial<AssetForm>) => setForm((f) => ({ ...f, ...patch }));

  const submit = async () => {
    if (!form.name.trim()) return toast.error("A name is required.");
    setBusy(true);
    try {
      await inventoryApi.assets.create({
        ...form,
        category: form.category || undefined,
        vendor: form.vendor || undefined,
        purchase_date: form.purchase_date || undefined,
        useful_life_months: Number(form.useful_life_months) || 0,
      });
      toast.success("Asset created.");
      setOpen(false);
      await load();
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-2">
        <div className="flex-1 min-w-[200px]">
          <Input label="Search" placeholder="Name, tag or serial…" value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
        <Select
          label="Status"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          options={[{ value: "", label: "All statuses" }, ...ASSET_STATUSES]}
        />
        <Button onClick={() => { setForm(empty); setOpen(true); }}>
          <Plus className="h-4 w-4" /> New asset
        </Button>
      </div>

      {loading ? (
        <div className="text-sm text-[var(--muted)]">Loading…</div>
      ) : rows.length === 0 ? (
        <EmptyState title="No assets" description="Register durable assets to track their lifecycle." />
      ) : (
        <Table>
          <thead>
            <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
              <th className="px-4 py-3 font-medium">Asset</th>
              <th className="px-4 py-3 font-medium">Category</th>
              <th className="px-4 py-3 font-medium text-right">Cost</th>
              <th className="px-4 py-3 font-medium">Condition</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((a) => (
              <tr key={a.id} className="border-b border-[var(--border)] last:border-0">
                <td className="px-4 py-3">
                  <div className="font-medium text-[var(--foreground)]">{a.name}</div>
                  <div className="font-mono text-xs text-[var(--muted)]">{a.asset_tag}</div>
                </td>
                <td className="px-4 py-3 text-[var(--foreground-secondary)]">{a.category_name || "—"}</td>
                <td className="px-4 py-3 text-right text-[var(--foreground-secondary)]">{formatMoney(a.purchase_cost)}</td>
                <td className="px-4 py-3"><StatusBadge status={a.condition} /></td>
                <td className="px-4 py-3"><StatusBadge status={a.status} /></td>
                <td className="px-4 py-3 text-right">
                  <Link href={`/inventory/assets/${a.id}`}>
                    <Button variant="ghost" size="sm"><Eye className="h-4 w-4" /></Button>
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      <Modal open={open} title="New asset" onClose={() => setOpen(false)}>
        <div className="max-h-[74vh] space-y-3 overflow-y-auto pr-1">
          <Input label="Name" value={form.name} onChange={(e) => set({ name: e.target.value })} />
          <div className="grid grid-cols-2 gap-3">
            <Select label="Category" value={form.category} onChange={(e) => set({ category: e.target.value })} placeholder="Uncategorized">
              {categories.map((c) => <option key={c.id} value={c.id}>{c.parent_name ? `${c.parent_name} / ${c.name}` : c.name}</option>)}
            </Select>
            <Select label="Vendor" value={form.vendor} onChange={(e) => set({ vendor: e.target.value })} placeholder="—">
              {vendors.map((v) => <option key={v.id} value={v.id}>{v.company_name}</option>)}
            </Select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Input label="Serial number" value={form.serial_number} onChange={(e) => set({ serial_number: e.target.value })} />
            <Input label="Purchase date" type="date" value={form.purchase_date} onChange={(e) => set({ purchase_date: e.target.value })} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Input label="Purchase cost" type="number" value={form.purchase_cost} onChange={(e) => set({ purchase_cost: e.target.value })} />
            <Select label="Condition" value={form.condition} onChange={(e) => set({ condition: e.target.value as Asset["condition"] })} options={ASSET_CONDITIONS} />
          </div>
          <div className="grid grid-cols-3 gap-3">
            <Input label="Useful life (mo)" type="number" value={form.useful_life_months} onChange={(e) => set({ useful_life_months: e.target.value })} />
            <Input label="Salvage value" type="number" value={form.salvage_value} onChange={(e) => set({ salvage_value: e.target.value })} />
            <Select label="Depreciation" value={form.depreciation_method} onChange={(e) => set({ depreciation_method: e.target.value })} options={DEPRECIATION_METHODS} />
          </div>
          <Input label="Department" value={form.department} onChange={(e) => set({ department: e.target.value })} />
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
            <Button loading={busy} onClick={submit}>Create</Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
