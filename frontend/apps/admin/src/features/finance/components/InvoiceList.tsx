"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
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
import { Ban, Eye, Plus, Send, Trash2 } from "lucide-react";

import { financeApi } from "../api/finance.api";
import type {
  AdjustmentKind,
  CreateInvoicePayload,
  Discount,
  FeeStructure,
  Invoice,
  ScholarshipAward,
} from "../types/finance.types";
import { StatusBadge, formatMoney } from "./primitives";
import { ResidentPicker } from "./ResidentPicker";

const STATUS_FILTERS = ["", "draft", "pending", "partial", "paid", "overdue", "cancelled", "refunded"];

type LineForm = {
  description: string;
  fee_structure: string;
  quantity: string;
  unit_price: string;
  tax_rate: string;
};

type AdjForm = {
  kind: AdjustmentKind;
  discount: string;
  scholarship_award: string;
  amount: string;
  note: string;
};

const emptyLine: LineForm = { description: "", fee_structure: "", quantity: "1", unit_price: "0", tax_rate: "0" };
const emptyAdj: AdjForm = { kind: "discount", discount: "", scholarship_award: "", amount: "", note: "" };

const num = (v: string) => {
  const n = parseFloat(v);
  return Number.isFinite(n) ? n : 0;
};

export function InvoiceList() {
  const toast = useToast();
  const confirm = useConfirm();
  const router = useRouter();

  const [rows, setRows] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  const [creating, setCreating] = useState(false);
  const [busy, setBusy] = useState(false);

  // Lookups for the create form.
  const [structures, setStructures] = useState<FeeStructure[]>([]);
  const [discounts, setDiscounts] = useState<Discount[]>([]);
  const [awards, setAwards] = useState<ScholarshipAward[]>([]);

  // Create-invoice form state.
  const [resident, setResident] = useState("");
  const [issueDate, setIssueDate] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [currency, setCurrency] = useState("NPR");
  const [notes, setNotes] = useState("");
  const [terms, setTerms] = useState("");
  const [asDraft, setAsDraft] = useState(false);
  const [lines, setLines] = useState<LineForm[]>([{ ...emptyLine }]);
  const [adjustments, setAdjustments] = useState<AdjForm[]>([]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows(await financeApi.invoices.list({ search, status: statusFilter }));
    } catch (e) {
      toast.error((e as Error).message, "Couldn't load invoices");
    } finally {
      setLoading(false);
    }
  }, [search, statusFilter, toast]);

  useEffect(() => {
    const t = setTimeout(load, 200);
    return () => clearTimeout(t);
  }, [load]);

  useEffect(() => {
    financeApi.feeStructures.list({ is_active: "true" }).then(setStructures).catch(() => {});
    financeApi.discounts.list().then(setDiscounts).catch(() => {});
    financeApi.scholarshipAwards.list({ status: "approved" }).then(setAwards).catch(() => {});
  }, []);

  const resetForm = () => {
    setResident("");
    setIssueDate("");
    setDueDate("");
    setCurrency("NPR");
    setNotes("");
    setTerms("");
    setAsDraft(false);
    setLines([{ ...emptyLine }]);
    setAdjustments([]);
  };

  const setLine = (i: number, patch: Partial<LineForm>) =>
    setLines((ls) => ls.map((l, idx) => (idx === i ? { ...l, ...patch } : l)));

  const onPickStructure = (i: number, structureId: string) => {
    const s = structures.find((x) => x.id === structureId);
    if (!s) {
      setLine(i, { fee_structure: "" });
      return;
    }
    setLine(i, {
      fee_structure: s.id,
      description: s.name,
      unit_price: s.amount,
      tax_rate: s.tax_rate,
    });
  };

  const setAdj = (i: number, patch: Partial<AdjForm>) =>
    setAdjustments((as) => as.map((a, idx) => (idx === i ? { ...a, ...patch } : a)));

  // Live client-side preview (final amounts are recomputed server-side).
  const preview = useMemo(() => {
    let subtotal = 0;
    let tax = 0;
    for (const l of lines) {
      const amount = num(l.quantity || "1") * num(l.unit_price);
      subtotal += amount;
      tax += (amount * num(l.tax_rate)) / 100;
    }
    let concessions = 0;
    for (const a of adjustments) {
      if (a.amount) {
        concessions += num(a.amount);
        continue;
      }
      if (a.kind === "discount" && a.discount) {
        const d = discounts.find((x) => x.id === a.discount);
        if (d) concessions += d.discount_type === "percentage" ? (subtotal * num(d.value)) / 100 : num(d.value);
      }
    }
    const total = Math.max(0, subtotal + tax - concessions);
    return { subtotal, tax, concessions, total };
  }, [lines, adjustments, discounts]);

  const submit = async () => {
    if (!resident) {
      toast.error("Select a resident for this invoice.");
      return;
    }
    const cleanLines = lines
      .filter((l) => l.description.trim() && num(l.unit_price) >= 0)
      .map((l) => {
        const line: CreateInvoicePayload["lines"][number] = {
          description: l.description.trim(),
          unit_price: l.unit_price || "0",
        };
        if (l.fee_structure) line.fee_structure = l.fee_structure;
        if (l.quantity) line.quantity = l.quantity;
        if (l.tax_rate) line.tax_rate = l.tax_rate;
        return line;
      });
    if (cleanLines.length === 0) {
      toast.error("Add at least one line item with a description.");
      return;
    }
    const cleanAdj = adjustments
      .filter((a) => a.amount || a.discount || a.scholarship_award || a.note)
      .map((a) => {
        const adj: NonNullable<CreateInvoicePayload["adjustments"]>[number] = { kind: a.kind };
        if (a.kind === "discount" && a.discount) adj.discount = a.discount;
        if (a.kind === "scholarship" && a.scholarship_award) adj.scholarship_award = a.scholarship_award;
        if (a.amount) adj.amount = a.amount;
        if (a.note) adj.note = a.note;
        return adj;
      });

    const payload: CreateInvoicePayload = {
      resident,
      currency: currency || "NPR",
      as_draft: asDraft,
      lines: cleanLines,
    };
    if (issueDate) payload.issue_date = issueDate;
    if (dueDate) payload.due_date = dueDate;
    if (notes) payload.notes = notes;
    if (terms) payload.terms = terms;
    if (cleanAdj.length) payload.adjustments = cleanAdj;

    setBusy(true);
    try {
      const created = await financeApi.invoices.create(payload);
      toast.success(`Invoice ${created.number} created.`);
      setCreating(false);
      resetForm();
      await load();
    } catch (e) {
      toast.error((e as Error).message, "Couldn't create invoice");
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

  const cancelInvoice = async (inv: Invoice) => {
    const yes = await confirm({
      title: "Cancel invoice",
      message: `Cancel invoice ${inv.number}? This can't be undone.`,
      danger: true,
      confirmText: "Cancel invoice",
      cancelText: "Keep",
    });
    if (yes) await act(() => financeApi.invoices.cancel(inv.id), "Invoice cancelled.");
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <div className="min-w-[200px] flex-1">
          <Input
            placeholder="Search by invoice number or resident…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="w-44">
          <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            {STATUS_FILTERS.map((s) => (
              <option key={s || "all"} value={s}>
                {s ? s[0].toUpperCase() + s.slice(1) : "All statuses"}
              </option>
            ))}
          </Select>
        </div>
        <Button onClick={() => setCreating(true)}>
          <Plus className="h-4 w-4" /> New invoice
        </Button>
      </div>

      {loading ? (
        <div className="text-sm text-[var(--muted)]">Loading…</div>
      ) : rows.length === 0 ? (
        <EmptyState title="No invoices yet" description="Raise your first invoice to start billing residents." />
      ) : (
        <Table>
          <thead>
            <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
              <th className="px-4 py-3 font-medium">Invoice</th>
              <th className="px-4 py-3 font-medium">Resident</th>
              <th className="px-4 py-3 font-medium">Issued</th>
              <th className="px-4 py-3 font-medium">Due</th>
              <th className="px-4 py-3 font-medium text-right">Total</th>
              <th className="px-4 py-3 font-medium text-right">Paid</th>
              <th className="px-4 py-3 font-medium text-right">Balance</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((inv) => (
              <tr key={inv.id} className="border-b border-[var(--border)] last:border-0">
                <td className="px-4 py-3">
                  <Link href={`/finance/invoices/${inv.id}`} className="font-medium text-[var(--foreground)] hover:text-[var(--accent)]">
                    {inv.number}
                  </Link>
                </td>
                <td className="px-4 py-3 text-[var(--foreground-secondary)]">{inv.resident_name}</td>
                <td className="px-4 py-3 text-[var(--foreground-secondary)]">{inv.issue_date}</td>
                <td className="px-4 py-3 text-[var(--foreground-secondary)]">{inv.due_date}</td>
                <td className="px-4 py-3 text-right text-[var(--foreground)]">{formatMoney(inv.total, inv.currency)}</td>
                <td className="px-4 py-3 text-right text-[var(--foreground-secondary)]">{formatMoney(inv.paid_amount, inv.currency)}</td>
                <td className="px-4 py-3 text-right font-semibold text-[var(--foreground)]">{formatMoney(inv.balance, inv.currency)}</td>
                <td className="px-4 py-3"><StatusBadge status={inv.status} /></td>
                <td className="px-4 py-3">
                  <div className="flex items-center justify-end gap-1">
                    <Button variant="ghost" size="sm" title="View" onClick={() => router.push(`/finance/invoices/${inv.id}`)}>
                      <Eye className="h-4 w-4" />
                    </Button>
                    {inv.status === "draft" ? (
                      <Button variant="ghost" size="sm" title="Issue" onClick={() => act(() => financeApi.invoices.issue(inv.id), "Invoice issued.")}>
                        <Send className="h-4 w-4" />
                      </Button>
                    ) : null}
                    {inv.status !== "cancelled" && inv.status !== "paid" ? (
                      <Button variant="ghost" size="sm" title="Cancel" onClick={() => cancelInvoice(inv)}>
                        <Ban className="h-4 w-4 text-[var(--error)]" />
                      </Button>
                    ) : null}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      <Modal open={creating} title="New invoice" onClose={() => setCreating(false)}>
        <div className="max-h-[74vh] space-y-4 overflow-y-auto pr-1">
          <ResidentPicker value={resident} onChange={setResident} />

          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <Input label="Issue date" type="date" value={issueDate} onChange={(e) => setIssueDate(e.target.value)} />
            <Input label="Due date" type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
            <Input label="Currency" value={currency} onChange={(e) => setCurrency(e.target.value)} />
          </div>

          {/* Line items */}
          <section className="space-y-2">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">Line items</h3>
              <Button variant="ghost" size="sm" onClick={() => setLines((ls) => [...ls, { ...emptyLine }])}>
                <Plus className="h-4 w-4" /> Add line
              </Button>
            </div>
            {lines.map((l, i) => (
              <div key={i} className="rounded-xl border border-[var(--border)] p-3 space-y-2">
                <div className="grid grid-cols-2 gap-2">
                  <Select
                    label="Fee structure (optional)"
                    value={l.fee_structure}
                    onChange={(e) => onPickStructure(i, e.target.value)}
                    placeholder="Custom line"
                  >
                    {structures.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name}
                      </option>
                    ))}
                  </Select>
                  <Input label="Description" value={l.description} onChange={(e) => setLine(i, { description: e.target.value })} />
                </div>
                <div className="grid grid-cols-3 gap-2">
                  <Input label="Qty" type="number" value={l.quantity} onChange={(e) => setLine(i, { quantity: e.target.value })} />
                  <Input label="Unit price" type="number" value={l.unit_price} onChange={(e) => setLine(i, { unit_price: e.target.value })} />
                  <Input label="Tax %" type="number" value={l.tax_rate} onChange={(e) => setLine(i, { tax_rate: e.target.value })} />
                </div>
                {lines.length > 1 ? (
                  <div className="flex justify-end">
                    <Button variant="ghost" size="sm" onClick={() => setLines((ls) => ls.filter((_, idx) => idx !== i))}>
                      <Trash2 className="h-4 w-4 text-[var(--error)]" /> Remove
                    </Button>
                  </div>
                ) : null}
              </div>
            ))}
          </section>

          {/* Adjustments */}
          <section className="space-y-2">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">Concessions (optional)</h3>
              <Button variant="ghost" size="sm" onClick={() => setAdjustments((as) => [...as, { ...emptyAdj }])}>
                <Plus className="h-4 w-4" /> Add
              </Button>
            </div>
            {adjustments.map((a, i) => (
              <div key={i} className="rounded-xl border border-[var(--border)] p-3 space-y-2">
                <div className="grid grid-cols-2 gap-2">
                  <Select label="Kind" value={a.kind} onChange={(e) => setAdj(i, { kind: e.target.value as AdjustmentKind })}>
                    <option value="discount">Discount</option>
                    <option value="scholarship">Scholarship</option>
                    <option value="waiver">Waiver</option>
                  </Select>
                  {a.kind === "discount" ? (
                    <Select label="Discount" value={a.discount} onChange={(e) => setAdj(i, { discount: e.target.value })} placeholder="Select discount">
                      {discounts.map((d) => (
                        <option key={d.id} value={d.id}>
                          {d.name}
                        </option>
                      ))}
                    </Select>
                  ) : a.kind === "scholarship" ? (
                    <Select label="Scholarship award" value={a.scholarship_award} onChange={(e) => setAdj(i, { scholarship_award: e.target.value })} placeholder="Select award">
                      {awards.map((aw) => (
                        <option key={aw.id} value={aw.id}>
                          {aw.scholarship_name} — {aw.resident_name}
                        </option>
                      ))}
                    </Select>
                  ) : (
                    <Input label="Amount" type="number" value={a.amount} onChange={(e) => setAdj(i, { amount: e.target.value })} />
                  )}
                </div>
                <div className="grid grid-cols-2 gap-2">
                  {a.kind !== "waiver" ? (
                    <Input label="Amount override (optional)" type="number" value={a.amount} onChange={(e) => setAdj(i, { amount: e.target.value })} />
                  ) : (
                    <div />
                  )}
                  <Input label="Note" value={a.note} onChange={(e) => setAdj(i, { note: e.target.value })} />
                </div>
                <div className="flex justify-end">
                  <Button variant="ghost" size="sm" onClick={() => setAdjustments((as) => as.filter((_, idx) => idx !== i))}>
                    <Trash2 className="h-4 w-4 text-[var(--error)]" /> Remove
                  </Button>
                </div>
              </div>
            ))}
          </section>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <Textarea label="Notes" value={notes} onChange={(e) => setNotes(e.target.value)} />
            <Textarea label="Terms" value={terms} onChange={(e) => setTerms(e.target.value)} />
          </div>

          <label className="flex items-center gap-2 text-sm text-[var(--foreground-secondary)]">
            <input type="checkbox" checked={asDraft} onChange={(e) => setAsDraft(e.target.checked)} />
            Save as draft (don&apos;t issue yet)
          </label>

          {/* Live preview */}
          <div className="rounded-xl border border-[var(--border)] bg-[var(--background-secondary)] p-3 text-sm">
            <div className="flex justify-between text-[var(--foreground-secondary)]">
              <span>Subtotal</span>
              <span>{formatMoney(preview.subtotal, currency)}</span>
            </div>
            <div className="flex justify-between text-[var(--foreground-secondary)]">
              <span>Tax</span>
              <span>{formatMoney(preview.tax, currency)}</span>
            </div>
            <div className="flex justify-between text-[var(--foreground-secondary)]">
              <span>Concessions</span>
              <span>− {formatMoney(preview.concessions, currency)}</span>
            </div>
            <div className="mt-1 flex justify-between border-t border-[var(--border)] pt-1 font-semibold text-[var(--foreground)]">
              <span>Estimated total</span>
              <span>{formatMoney(preview.total, currency)}</span>
            </div>
            <p className="mt-1 text-[11px] text-[var(--muted)]">Final amounts are recalculated on save.</p>
          </div>

          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setCreating(false)}>
              Cancel
            </Button>
            <Button loading={busy} onClick={submit}>
              Create invoice
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
