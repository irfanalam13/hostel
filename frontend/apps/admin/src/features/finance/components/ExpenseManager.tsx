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
import { Check, Pencil, Plus, Trash2, X } from "lucide-react";

import { financeApi } from "../api/finance.api";
import { EXPENSE_RECURRENCES, PAYMENT_METHODS } from "../constants";
import type { Expense, ExpenseCategory, ExpenseStatus } from "../types/finance.types";
import { StatusBadge, formatMoney } from "./primitives";

const STATUS_FILTERS: { value: ExpenseStatus | ""; label: string }[] = [
  { value: "", label: "All statuses" },
  { value: "pending", label: "Pending" },
  { value: "approved", label: "Approved" },
  { value: "rejected", label: "Rejected" },
  { value: "paid", label: "Paid" },
];

type ExpenseForm = {
  category: string;
  title: string;
  description: string;
  amount: string;
  tax_amount: string;
  expense_date: string;
  payment_method: Expense["payment_method"];
  vendor_name: string;
  vendor_contact: string;
  reference: string;
  recurrence: Expense["recurrence"];
};

const emptyExpense: ExpenseForm = {
  category: "",
  title: "",
  description: "",
  amount: "0",
  tax_amount: "0",
  expense_date: "",
  payment_method: "cash",
  vendor_name: "",
  vendor_contact: "",
  reference: "",
  recurrence: "none",
};

export function ExpenseManager() {
  const toast = useToast();
  const confirm = useConfirm();

  const [rows, setRows] = useState<Expense[]>([]);
  const [categories, setCategories] = useState<ExpenseCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<ExpenseStatus | "">("");

  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Expense | null>(null);
  const [form, setForm] = useState<ExpenseForm>(emptyExpense);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows(await financeApi.expenses.list({ search, status: statusFilter || undefined }));
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
    financeApi.expenseCategories.list().then(setCategories).catch(() => {});
  }, []);

  const set = (patch: Partial<ExpenseForm>) => setForm((f) => ({ ...f, ...patch }));

  const totals = useMemo(() => {
    const paid = rows
      .filter((r) => r.status === "paid")
      .reduce((sum, r) => sum + parseFloat(r.amount || "0") + parseFloat(r.tax_amount || "0"), 0);
    const pending = rows.filter((r) => r.status === "pending").length;
    return { paid, pending };
  }, [rows]);

  const startCreate = () => {
    setEditing(null);
    setForm({ ...emptyExpense, category: categories[0]?.id ?? "" });
    setOpen(true);
  };
  const startEdit = (x: Expense) => {
    setEditing(x);
    setForm({
      category: x.category,
      title: x.title,
      description: x.description,
      amount: x.amount,
      tax_amount: x.tax_amount,
      expense_date: x.expense_date,
      payment_method: x.payment_method,
      vendor_name: x.vendor_name,
      vendor_contact: x.vendor_contact,
      reference: x.reference,
      recurrence: x.recurrence,
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
      const body: Partial<Expense> = {
        category: form.category || undefined,
        title: form.title.trim(),
        description: form.description,
        amount: form.amount || "0",
        tax_amount: form.tax_amount || "0",
        expense_date: form.expense_date || undefined,
        payment_method: form.payment_method,
        vendor_name: form.vendor_name,
        vendor_contact: form.vendor_contact,
        reference: form.reference,
        recurrence: form.recurrence,
      };
      if (editing) await financeApi.expenses.update(editing.id, body);
      else await financeApi.expenses.create(body);
      toast.success(editing ? "Expense updated." : "Expense added.");
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

  const remove = async (x: Expense) => {
    const yes = await confirm({
      title: "Delete expense",
      message: `Delete "${x.title}"?`,
      danger: true,
      confirmText: "Delete",
    });
    if (yes) await act(() => financeApi.expenses.remove(x.id), "Expense deleted.");
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-2">
        <div className="flex-1 min-w-[200px]">
          <Input
            label="Search"
            placeholder="Title, vendor or reference…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <Select
          label="Status"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as ExpenseStatus | "")}
          options={STATUS_FILTERS}
        />
        <Button onClick={startCreate}>
          <Plus className="h-4 w-4" /> Add expense
        </Button>
      </div>

      <div className="flex flex-wrap gap-2 text-xs text-[var(--muted)]">
        <span>Paid this list: <strong className="text-[var(--foreground)]">{formatMoney(totals.paid)}</strong></span>
        <span>· {totals.pending} awaiting approval</span>
      </div>

      {loading ? (
        <div className="text-sm text-[var(--muted)]">Loading…</div>
      ) : rows.length === 0 ? (
        <EmptyState title="No expenses" description="Record operational expenses and route them through approval." />
      ) : (
        <Table>
          <thead>
            <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
              <th className="px-4 py-3 font-medium">Title</th>
              <th className="px-4 py-3 font-medium">Category</th>
              <th className="px-4 py-3 font-medium">Date</th>
              <th className="px-4 py-3 font-medium text-right">Amount</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((x) => (
              <tr key={x.id} className="border-b border-[var(--border)] last:border-0">
                <td className="px-4 py-3">
                  <div className="font-medium text-[var(--foreground)]">{x.title}</div>
                  {x.vendor_name ? <div className="text-xs text-[var(--muted)]">{x.vendor_name}</div> : null}
                </td>
                <td className="px-4 py-3 text-[var(--foreground-secondary)]">{x.category_name || "—"}</td>
                <td className="px-4 py-3 text-[var(--foreground-secondary)]">{x.expense_date}</td>
                <td className="px-4 py-3 text-right text-[var(--foreground)]">
                  {formatMoney(parseFloat(x.amount || "0") + parseFloat(x.tax_amount || "0"))}
                </td>
                <td className="px-4 py-3"><StatusBadge status={x.status} /></td>
                <td className="px-4 py-3">
                  <div className="flex items-center justify-end gap-1">
                    {x.status === "pending" ? (
                      <>
                        <Button variant="ghost" size="sm" title="Approve" onClick={() => act(() => financeApi.expenses.approve(x.id), "Expense approved.")}>
                          <Check className="h-4 w-4 text-[var(--success)]" />
                        </Button>
                        <Button variant="ghost" size="sm" title="Reject" onClick={() => act(() => financeApi.expenses.reject(x.id), "Expense rejected.")}>
                          <X className="h-4 w-4 text-[var(--error)]" />
                        </Button>
                      </>
                    ) : null}
                    {x.status === "pending" || x.status === "approved" ? (
                      <Button variant="ghost" size="sm" title="Mark paid" onClick={() => act(() => financeApi.expenses.markPaid(x.id), "Expense marked paid.")}>
                        Pay
                      </Button>
                    ) : null}
                    {x.status !== "paid" ? (
                      <>
                        <Button variant="ghost" size="sm" title="Edit" onClick={() => startEdit(x)}>
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="sm" title="Delete" onClick={() => remove(x)}>
                          <Trash2 className="h-4 w-4 text-[var(--error)]" />
                        </Button>
                      </>
                    ) : null}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      <Modal open={open} title={editing ? "Edit expense" : "Add expense"} onClose={() => setOpen(false)}>
        <div className="max-h-[74vh] space-y-3 overflow-y-auto pr-1">
          <div className="grid grid-cols-2 gap-3">
            <Input label="Title" value={form.title} onChange={(e) => set({ title: e.target.value })} />
            <Select label="Category" value={form.category} onChange={(e) => set({ category: e.target.value })} placeholder="Uncategorized">
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </Select>
          </div>
          <Textarea label="Description" value={form.description} onChange={(e) => set({ description: e.target.value })} />
          <div className="grid grid-cols-3 gap-3">
            <Input label="Amount" type="number" value={form.amount} onChange={(e) => set({ amount: e.target.value })} />
            <Input label="Tax amount" type="number" value={form.tax_amount} onChange={(e) => set({ tax_amount: e.target.value })} />
            <Input label="Date" type="date" value={form.expense_date} onChange={(e) => set({ expense_date: e.target.value })} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Select label="Payment method" value={form.payment_method} onChange={(e) => set({ payment_method: e.target.value as Expense["payment_method"] })} options={PAYMENT_METHODS} />
            <Select label="Recurrence" value={form.recurrence} onChange={(e) => set({ recurrence: e.target.value as Expense["recurrence"] })} options={EXPENSE_RECURRENCES} />
          </div>
          <div className="grid grid-cols-3 gap-3">
            <Input label="Vendor" value={form.vendor_name} onChange={(e) => set({ vendor_name: e.target.value })} />
            <Input label="Vendor contact" value={form.vendor_contact} onChange={(e) => set({ vendor_contact: e.target.value })} />
            <Input label="Reference" value={form.reference} onChange={(e) => set({ reference: e.target.value })} />
          </div>
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
