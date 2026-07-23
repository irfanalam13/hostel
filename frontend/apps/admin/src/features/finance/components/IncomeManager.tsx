"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
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
import { INCOME_SOURCES, PAYMENT_METHODS, methodLabel } from "../constants";
import type { Income } from "../types/finance.types";
import { formatMoney } from "./primitives";

const SOURCE_FILTERS = [{ value: "", label: "All sources" }, ...INCOME_SOURCES];

type IncomeForm = {
  source: Income["source"];
  title: string;
  description: string;
  amount: string;
  income_date: string;
  payment_method: Income["payment_method"];
  reference: string;
};

const emptyIncome: IncomeForm = {
  source: "other",
  title: "",
  description: "",
  amount: "0",
  income_date: "",
  payment_method: "cash",
  reference: "",
};

export function IncomeManager() {
  const toast = useToast();
  const confirm = useConfirm();

  const [rows, setRows] = useState<Income[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [sourceFilter, setSourceFilter] = useState("");

  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Income | null>(null);
  const [form, setForm] = useState<IncomeForm>(emptyIncome);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows(await financeApi.income.list({ search, source: sourceFilter || undefined }));
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [search, sourceFilter, toast]);

  useEffect(() => {
    const t = setTimeout(load, 200);
    return () => clearTimeout(t);
  }, [load]);

  const set = (patch: Partial<IncomeForm>) => setForm((f) => ({ ...f, ...patch }));

  const total = useMemo(
    () => rows.reduce((sum, r) => sum + parseFloat(r.amount || "0"), 0),
    [rows],
  );

  const startCreate = () => {
    setEditing(null);
    setForm(emptyIncome);
    setOpen(true);
  };
  const startEdit = (x: Income) => {
    setEditing(x);
    setForm({
      source: x.source,
      title: x.title,
      description: x.description,
      amount: x.amount,
      income_date: x.income_date,
      payment_method: x.payment_method,
      reference: x.reference,
    });
    setOpen(true);
  };

  const submit = async () => {
    if (!form.title.trim()) {
      toast.error("A title is required.");
      return;
    }
    setBusy(true);
    try {
      const body: Partial<Income> = {
        source: form.source,
        title: form.title.trim(),
        description: form.description,
        amount: form.amount || "0",
        income_date: form.income_date || undefined,
        payment_method: form.payment_method,
        reference: form.reference,
      };
      if (editing) await financeApi.income.update(editing.id, body);
      else await financeApi.income.create(body);
      toast.success(editing ? "Income updated." : "Income recorded.");
      setOpen(false);
      await load();
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const remove = async (x: Income) => {
    const yes = await confirm({
      title: "Delete income",
      message: `Delete "${x.title}"?`,
      danger: true,
      confirmText: "Delete",
    });
    if (!yes) return;
    try {
      await financeApi.income.remove(x.id);
      toast.success("Income deleted.");
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
            placeholder="Title or reference…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <Select
          label="Source"
          value={sourceFilter}
          onChange={(e) => setSourceFilter(e.target.value)}
          options={SOURCE_FILTERS}
        />
        <Button onClick={startCreate}>
          <Plus className="h-4 w-4" /> Add income
        </Button>
      </div>

      <div className="text-xs text-[var(--muted)]">
        Total in this list: <strong className="text-[var(--foreground)]">{formatMoney(total)}</strong>
      </div>

      {loading ? (
        <div className="text-sm text-[var(--muted)]">Loading…</div>
      ) : rows.length === 0 ? (
        <EmptyState title="No income recorded" description="Log ancillary income like cafeteria, laundry or donations." />
      ) : (
        <Table>
          <thead>
            <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
              <th className="px-4 py-3 font-medium">Title</th>
              <th className="px-4 py-3 font-medium">Source</th>
              <th className="px-4 py-3 font-medium">Date</th>
              <th className="px-4 py-3 font-medium">Method</th>
              <th className="px-4 py-3 font-medium text-right">Amount</th>
              <th className="px-4 py-3 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((x) => (
              <tr key={x.id} className="border-b border-[var(--border)] last:border-0">
                <td className="px-4 py-3 font-medium text-[var(--foreground)]">{x.title}</td>
                <td className="px-4 py-3 capitalize text-[var(--foreground-secondary)]">{x.source.replace(/_/g, " ")}</td>
                <td className="px-4 py-3 text-[var(--foreground-secondary)]">{x.income_date}</td>
                <td className="px-4 py-3 text-[var(--foreground-secondary)]">{methodLabel(x.payment_method)}</td>
                <td className="px-4 py-3 text-right text-[var(--foreground)]">{formatMoney(x.amount)}</td>
                <td className="px-4 py-3">
                  <div className="flex items-center justify-end gap-1">
                    <Button variant="ghost" size="sm" title="Edit" onClick={() => startEdit(x)}>
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="sm" title="Delete" onClick={() => remove(x)}>
                      <Trash2 className="h-4 w-4 text-[var(--error)]" />
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      <Modal open={open} title={editing ? "Edit income" : "Add income"} onClose={() => setOpen(false)}>
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <Input label="Title" value={form.title} onChange={(e) => set({ title: e.target.value })} />
            <Select label="Source" value={form.source} onChange={(e) => set({ source: e.target.value as Income["source"] })} options={INCOME_SOURCES} />
          </div>
          <Textarea label="Description" value={form.description} onChange={(e) => set({ description: e.target.value })} />
          <div className="grid grid-cols-3 gap-3">
            <Input label="Amount" type="number" value={form.amount} onChange={(e) => set({ amount: e.target.value })} />
            <Input label="Date" type="date" value={form.income_date} onChange={(e) => set({ income_date: e.target.value })} />
            <Select label="Method" value={form.payment_method} onChange={(e) => set({ payment_method: e.target.value as Income["payment_method"] })} options={PAYMENT_METHODS} />
          </div>
          <Input label="Reference" value={form.reference} onChange={(e) => set({ reference: e.target.value })} />
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button loading={busy} onClick={submit}>
              {editing ? "Save" : "Add"}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
