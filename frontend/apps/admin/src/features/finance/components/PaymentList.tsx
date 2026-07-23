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
import { Ban, BadgeCheck, Plus, XCircle } from "lucide-react";

import { financeApi } from "../api/finance.api";
import { PAYMENT_METHODS, methodLabel } from "../constants";
import type { CreatePaymentPayload, Invoice, Payment, PaymentMethod } from "../types/finance.types";
import { StatusBadge, formatMoney } from "./primitives";
import { ResidentPicker } from "./ResidentPicker";

const STATUS_FILTERS = ["", "pending", "verified", "failed", "cancelled", "refunded"];

export function PaymentList() {
  const toast = useToast();
  const confirm = useConfirm();

  const [rows, setRows] = useState<Payment[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [methodFilter, setMethodFilter] = useState("");

  const [collecting, setCollecting] = useState(false);
  const [busy, setBusy] = useState(false);

  // Collect-payment form.
  const [mode, setMode] = useState<"resident" | "invoice">("resident");
  const [resident, setResident] = useState("");
  const [invoiceId, setInvoiceId] = useState("");
  const [invoiceSearch, setInvoiceSearch] = useState("");
  const [invoiceOptions, setInvoiceOptions] = useState<Invoice[]>([]);
  const [amount, setAmount] = useState("");
  const [method, setMethod] = useState<PaymentMethod>("cash");
  const [reference, setReference] = useState("");
  const [note, setNote] = useState("");
  const [requireVerification, setRequireVerification] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows(await financeApi.payments.list({ search, status: statusFilter, method: methodFilter }));
    } catch (e) {
      toast.error((e as Error).message, "Couldn't load payments");
    } finally {
      setLoading(false);
    }
  }, [search, statusFilter, methodFilter, toast]);

  useEffect(() => {
    const t = setTimeout(load, 200);
    return () => clearTimeout(t);
  }, [load]);

  // Invoice picker options (only when collecting by invoice).
  useEffect(() => {
    if (!collecting || mode !== "invoice") return;
    let active = true;
    const t = setTimeout(() => {
      financeApi.invoices
        .list({ search: invoiceSearch })
        .then((r) => {
          if (active) setInvoiceOptions(r);
        })
        .catch(() => {});
    }, 200);
    return () => {
      active = false;
      clearTimeout(t);
    };
  }, [collecting, mode, invoiceSearch]);

  const resetForm = () => {
    setMode("resident");
    setResident("");
    setInvoiceId("");
    setInvoiceSearch("");
    setAmount("");
    setMethod("cash");
    setReference("");
    setNote("");
    setRequireVerification(false);
  };

  const submit = async () => {
    if (mode === "resident" && !resident) {
      toast.error("Select a resident.");
      return;
    }
    if (mode === "invoice" && !invoiceId) {
      toast.error("Select an invoice.");
      return;
    }
    if (!amount || Number(amount) <= 0) {
      toast.error("Enter a payment amount.");
      return;
    }
    setBusy(true);
    try {
      const payload: CreatePaymentPayload = {
        amount,
        method,
        require_verification: requireVerification,
      };
      if (mode === "resident") payload.resident = resident;
      else payload.invoice = invoiceId;
      if (reference) payload.reference = reference;
      if (note) payload.note = note;
      const created = await financeApi.payments.create(payload);
      toast.success(`Payment ${created.receipt_number || ""} recorded.`.trim());
      setCollecting(false);
      resetForm();
      await load();
    } catch (e) {
      toast.error((e as Error).message, "Couldn't record payment");
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

  const cancelPayment = async (p: Payment) => {
    const yes = await confirm({
      title: "Cancel payment",
      message: `Cancel payment ${p.receipt_number || ""}?`.trim(),
      danger: true,
      confirmText: "Cancel payment",
      cancelText: "Keep",
    });
    if (yes) await act(() => financeApi.payments.cancel(p.id), "Payment cancelled.");
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <div className="min-w-[200px] flex-1">
          <Input
            placeholder="Search by receipt, resident or invoice…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="w-40">
          <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            {STATUS_FILTERS.map((s) => (
              <option key={s || "all"} value={s}>
                {s ? s[0].toUpperCase() + s.slice(1) : "All statuses"}
              </option>
            ))}
          </Select>
        </div>
        <div className="w-44">
          <Select value={methodFilter} onChange={(e) => setMethodFilter(e.target.value)} placeholder="All methods">
            {PAYMENT_METHODS.map((m) => (
              <option key={m.value} value={m.value}>
                {m.label}
              </option>
            ))}
          </Select>
        </div>
        <Button onClick={() => setCollecting(true)}>
          <Plus className="h-4 w-4" /> Collect payment
        </Button>
      </div>

      {loading ? (
        <div className="text-sm text-[var(--muted)]">Loading…</div>
      ) : rows.length === 0 ? (
        <EmptyState title="No payments yet" description="Collect a payment to see receipts here." />
      ) : (
        <Table>
          <thead>
            <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
              <th className="px-4 py-3 font-medium">Receipt</th>
              <th className="px-4 py-3 font-medium">Resident</th>
              <th className="px-4 py-3 font-medium">Invoice</th>
              <th className="px-4 py-3 font-medium text-right">Amount</th>
              <th className="px-4 py-3 font-medium">Method</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Received</th>
              <th className="px-4 py-3 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((p) => (
              <tr key={p.id} className="border-b border-[var(--border)] last:border-0">
                <td className="px-4 py-3 font-medium text-[var(--foreground)]">{p.receipt_number || "—"}</td>
                <td className="px-4 py-3 text-[var(--foreground-secondary)]">{p.resident_name || "—"}</td>
                <td className="px-4 py-3 text-[var(--foreground-secondary)]">{p.invoice_number || "—"}</td>
                <td className="px-4 py-3 text-right font-semibold text-[var(--foreground)]">{formatMoney(p.amount)}</td>
                <td className="px-4 py-3 text-[var(--foreground-secondary)]">{methodLabel(p.method)}</td>
                <td className="px-4 py-3"><StatusBadge status={p.status} /></td>
                <td className="px-4 py-3 text-[var(--foreground-secondary)]">
                  {p.received_at ? new Date(p.received_at).toLocaleDateString() : "—"}
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center justify-end gap-1">
                    {p.status === "pending" ? (
                      <Button variant="ghost" size="sm" title="Verify" onClick={() => act(() => financeApi.payments.verify(p.id), "Payment verified.")}>
                        <BadgeCheck className="h-4 w-4 text-[var(--success)]" />
                      </Button>
                    ) : null}
                    {p.status !== "cancelled" && p.status !== "failed" ? (
                      <>
                        <Button variant="ghost" size="sm" title="Mark failed" onClick={() => act(() => financeApi.payments.fail(p.id), "Payment marked failed.")}>
                          <XCircle className="h-4 w-4 text-[var(--warning)]" />
                        </Button>
                        <Button variant="ghost" size="sm" title="Cancel" onClick={() => cancelPayment(p)}>
                          <Ban className="h-4 w-4 text-[var(--error)]" />
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

      <Modal open={collecting} title="Collect payment" onClose={() => setCollecting(false)}>
        <div className="max-h-[74vh] space-y-3 overflow-y-auto pr-1">
          <Select label="Apply to" value={mode} onChange={(e) => setMode(e.target.value as "resident" | "invoice")}>
            <option value="resident">A resident (open balance)</option>
            <option value="invoice">A specific invoice</option>
          </Select>

          {mode === "resident" ? (
            <ResidentPicker value={resident} onChange={setResident} />
          ) : (
            <div className="space-y-2">
              <Input
                label="Invoice"
                placeholder="Search invoices by number or resident…"
                value={invoiceSearch}
                onChange={(e) => setInvoiceSearch(e.target.value)}
              />
              <Select aria-label="Invoice" value={invoiceId} onChange={(e) => setInvoiceId(e.target.value)} placeholder="Select an invoice">
                {invoiceOptions.map((inv) => (
                  <option key={inv.id} value={inv.id}>
                    {inv.number} — {inv.resident_name} ({formatMoney(inv.balance, inv.currency)} due)
                  </option>
                ))}
              </Select>
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <Input label="Amount" type="number" value={amount} onChange={(e) => setAmount(e.target.value)} />
            <Select label="Method" value={method} onChange={(e) => setMethod(e.target.value as PaymentMethod)} options={PAYMENT_METHODS} />
          </div>
          <Input label="Reference (optional)" value={reference} onChange={(e) => setReference(e.target.value)} />
          <Textarea label="Note (optional)" value={note} onChange={(e) => setNote(e.target.value)} />
          <label className="flex items-center gap-2 text-sm text-[var(--foreground-secondary)]">
            <input type="checkbox" checked={requireVerification} onChange={(e) => setRequireVerification(e.target.checked)} />
            Park as pending (requires verification)
          </label>

          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setCollecting(false)}>
              Cancel
            </Button>
            <Button loading={busy} onClick={submit}>
              Record payment
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
