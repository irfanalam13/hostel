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

import { financeApi } from "../api/finance.api";
import { DISCOUNT_REASONS, DISCOUNT_TYPES } from "../constants";
import type { Discount, DiscountReason, DiscountType } from "../types/finance.types";
import { StatusBadge, formatMoney } from "./primitives";

type DiscountForm = {
  name: string;
  discount_type: DiscountType;
  value: string;
  reason: DiscountReason;
  description: string;
  valid_from: string;
  valid_until: string;
  max_uses: string;
  is_active: boolean;
};

const emptyDiscount: DiscountForm = {
  name: "",
  discount_type: "percentage",
  value: "0",
  reason: "custom",
  description: "",
  valid_from: "",
  valid_until: "",
  max_uses: "",
  is_active: true,
};

function discountValue(d: Discount): string {
  return d.discount_type === "percentage" ? `${parseFloat(d.value)}%` : formatMoney(d.value);
}

export function DiscountManager() {
  const toast = useToast();
  const confirm = useConfirm();

  const [rows, setRows] = useState<Discount[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Discount | null>(null);
  const [form, setForm] = useState<DiscountForm>(emptyDiscount);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows(await financeApi.discounts.list({ search }));
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [search, toast]);

  useEffect(() => {
    const t = setTimeout(load, 200);
    return () => clearTimeout(t);
  }, [load]);

  const set = (patch: Partial<DiscountForm>) => setForm((f) => ({ ...f, ...patch }));

  const startCreate = () => {
    setEditing(null);
    setForm(emptyDiscount);
    setOpen(true);
  };
  const startEdit = (d: Discount) => {
    setEditing(d);
    setForm({
      name: d.name,
      discount_type: d.discount_type,
      value: d.value,
      reason: d.reason,
      description: d.description,
      valid_from: d.valid_from ?? "",
      valid_until: d.valid_until ?? "",
      max_uses: d.max_uses != null ? String(d.max_uses) : "",
      is_active: d.is_active,
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
      const body: Partial<Discount> = {
        name: form.name.trim(),
        discount_type: form.discount_type,
        value: form.value || "0",
        reason: form.reason,
        description: form.description,
        valid_from: form.valid_from || null,
        valid_until: form.valid_until || null,
        max_uses: form.max_uses ? Number(form.max_uses) : null,
        is_active: form.is_active,
      };
      if (editing) await financeApi.discounts.update(editing.id, body);
      else await financeApi.discounts.create(body);
      toast.success(editing ? "Discount updated." : "Discount created.");
      setOpen(false);
      await load();
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const remove = async (d: Discount) => {
    const yes = await confirm({
      title: "Delete discount",
      message: `Delete "${d.name}"?`,
      danger: true,
      confirmText: "Delete",
    });
    if (!yes) return;
    try {
      await financeApi.discounts.remove(d.id);
      toast.success("Discount deleted.");
      await load();
    } catch (e) {
      toast.error((e as Error).message);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-2">
        <div className="flex-1 min-w-[200px]">
          <Input
            label="Search"
            placeholder="Discount name…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <Button onClick={startCreate}>
          <Plus className="h-4 w-4" /> New discount
        </Button>
      </div>

      {loading ? (
        <div className="text-sm text-[var(--muted)]">Loading…</div>
      ) : rows.length === 0 ? (
        <EmptyState title="No discounts" description="Create discount schemes to apply to invoices." />
      ) : (
        <Table>
          <thead>
            <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
              <th className="px-4 py-3 font-medium">Name</th>
              <th className="px-4 py-3 font-medium">Reason</th>
              <th className="px-4 py-3 font-medium text-right">Value</th>
              <th className="px-4 py-3 font-medium text-right">Used</th>
              <th className="px-4 py-3 font-medium">Active</th>
              <th className="px-4 py-3 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((d) => (
              <tr key={d.id} className="border-b border-[var(--border)] last:border-0">
                <td className="px-4 py-3 font-medium text-[var(--foreground)]">{d.name}</td>
                <td className="px-4 py-3 capitalize text-[var(--foreground-secondary)]">{d.reason.replace(/_/g, " ")}</td>
                <td className="px-4 py-3 text-right text-[var(--foreground)]">{discountValue(d)}</td>
                <td className="px-4 py-3 text-right text-[var(--foreground-secondary)]">
                  {d.used_count}{d.max_uses != null ? ` / ${d.max_uses}` : ""}
                </td>
                <td className="px-4 py-3">
                  <StatusBadge status={d.is_active ? "active" : "ended"} label={d.is_active ? "Active" : "Inactive"} />
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center justify-end gap-1">
                    <Button variant="ghost" size="sm" title="Edit" onClick={() => startEdit(d)}>
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="sm" title="Delete" onClick={() => remove(d)}>
                      <Trash2 className="h-4 w-4 text-[var(--error)]" />
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      <Modal open={open} title={editing ? "Edit discount" : "New discount"} onClose={() => setOpen(false)}>
        <div className="space-y-3">
          <Input label="Name" value={form.name} onChange={(e) => set({ name: e.target.value })} />
          <div className="grid grid-cols-3 gap-3">
            <Select label="Type" value={form.discount_type} onChange={(e) => set({ discount_type: e.target.value as DiscountType })} options={DISCOUNT_TYPES} />
            <Input label={form.discount_type === "percentage" ? "Value %" : "Amount"} type="number" value={form.value} onChange={(e) => set({ value: e.target.value })} />
            <Select label="Reason" value={form.reason} onChange={(e) => set({ reason: e.target.value as DiscountReason })} options={DISCOUNT_REASONS} />
          </div>
          <Textarea label="Description" value={form.description} onChange={(e) => set({ description: e.target.value })} />
          <div className="grid grid-cols-3 gap-3">
            <Input label="Valid from" type="date" value={form.valid_from} onChange={(e) => set({ valid_from: e.target.value })} />
            <Input label="Valid until" type="date" value={form.valid_until} onChange={(e) => set({ valid_until: e.target.value })} />
            <Input label="Max uses" type="number" value={form.max_uses} onChange={(e) => set({ max_uses: e.target.value })} />
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
