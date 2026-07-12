"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  Button,
  Card,
  ErrorState,
  Input,
  Modal,
  Select,
  Textarea,
  useConfirm,
  useToast,
} from "@hostel/ui";
import { ArrowLeft, Ban, Plus, Send } from "lucide-react";
import { useApi } from "@hostel/hooks";

import { financeApi } from "../api/finance.api";
import { PAYMENT_METHODS } from "../constants";
import type { CreatePaymentPayload, PaymentMethod } from "../types/finance.types";
import { ReadField, StatusBadge, formatMoney } from "./primitives";

export function InvoiceDetail({ invoiceId }: { invoiceId: string }) {
  const toast = useToast();
  const confirm = useConfirm();

  const { data: invoice, loading, error, refetch } = useApi(
    () => financeApi.invoices.retrieve(invoiceId),
    { deps: [invoiceId], toastOnError: false },
  );

  const [paying, setPaying] = useState(false);
  const [busy, setBusy] = useState(false);
  const [amount, setAmount] = useState("");
  const [method, setMethod] = useState<PaymentMethod>("cash");
  const [reference, setReference] = useState("");
  const [note, setNote] = useState("");
  const [requireVerification, setRequireVerification] = useState(false);

  // Prefill the payment amount with the outstanding balance when opening.
  useEffect(() => {
    if (paying && invoice) setAmount(invoice.balance);
  }, [paying, invoice]);

  const act = async (fn: () => Promise<unknown>, ok: string) => {
    try {
      await fn();
      toast.success(ok);
      await refetch();
    } catch (e) {
      toast.error((e as Error).message);
    }
  };

  const cancelInvoice = async () => {
    if (!invoice) return;
    const yes = await confirm({
      title: "Cancel invoice",
      message: `Cancel invoice ${invoice.number}? This can't be undone.`,
      danger: true,
      confirmText: "Cancel invoice",
      cancelText: "Keep",
    });
    if (yes) await act(() => financeApi.invoices.cancel(invoice.id), "Invoice cancelled.");
  };

  const recordPayment = async () => {
    if (!invoice) return;
    setBusy(true);
    try {
      const payload: CreatePaymentPayload = {
        invoice: invoice.id,
        amount: amount || "0",
        method,
        require_verification: requireVerification,
      };
      if (reference) payload.reference = reference;
      if (note) payload.note = note;
      await financeApi.payments.create(payload);
      toast.success("Payment recorded.");
      setPaying(false);
      setReference("");
      setNote("");
      setRequireVerification(false);
      await refetch();
    } catch (e) {
      toast.error((e as Error).message, "Couldn't record payment");
    } finally {
      setBusy(false);
    }
  };

  if (loading) return <div className="text-sm text-[var(--muted)]">Loading…</div>;
  if (error || !invoice) return <ErrorState description={error || "Invoice not found."} onRetry={refetch} />;

  return (
    <div className="space-y-5">
      <Link href="/finance/invoices" className="inline-flex items-center gap-1.5 text-sm text-[var(--muted)] hover:text-[var(--foreground)]">
        <ArrowLeft className="h-4 w-4" /> Back to invoices
      </Link>

      <Card>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-semibold text-[var(--foreground)]">{invoice.number}</h2>
              <StatusBadge status={invoice.status} />
            </div>
            <div className="mt-0.5 text-sm text-[var(--muted)]">{invoice.resident_name}</div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {invoice.status === "draft" ? (
              <Button variant="secondary" onClick={() => act(() => financeApi.invoices.issue(invoice.id), "Invoice issued.")}>
                <Send className="h-4 w-4" /> Issue
              </Button>
            ) : null}
            {invoice.status !== "cancelled" && invoice.status !== "paid" ? (
              <Button onClick={() => setPaying(true)}>
                <Plus className="h-4 w-4" /> Record payment
              </Button>
            ) : null}
            {invoice.status !== "cancelled" && invoice.status !== "paid" ? (
              <Button variant="ghost" onClick={cancelInvoice}>
                <Ban className="h-4 w-4 text-[var(--error)]" /> Cancel
              </Button>
            ) : null}
          </div>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-4 border-t border-[var(--border)] pt-4 md:grid-cols-4">
          <ReadField label="Issue date" value={invoice.issue_date} />
          <ReadField label="Due date" value={invoice.due_date} />
          <ReadField label="Currency" value={invoice.currency} />
          <ReadField label="Created" value={invoice.created_at ? new Date(invoice.created_at).toLocaleDateString() : "—"} />
        </div>
      </Card>

      {/* Line items */}
      <Card>
        <h3 className="mb-3 text-sm font-semibold text-[var(--foreground-secondary)]">Line items</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-[var(--border)] text-[var(--muted)]">
                <th className="py-2 pr-3 font-medium">Description</th>
                <th className="py-2 pr-3 font-medium text-right">Qty</th>
                <th className="py-2 pr-3 font-medium text-right">Unit price</th>
                <th className="py-2 pr-3 font-medium text-right">Tax %</th>
                <th className="py-2 pr-3 font-medium text-right">Tax</th>
                <th className="py-2 font-medium text-right">Amount</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border)]">
              {invoice.lines.map((l) => (
                <tr key={l.id}>
                  <td className="py-2.5 pr-3 text-[var(--foreground)]">{l.description}</td>
                  <td className="py-2.5 pr-3 text-right text-[var(--foreground-secondary)]">{l.quantity}</td>
                  <td className="py-2.5 pr-3 text-right text-[var(--foreground-secondary)]">{formatMoney(l.unit_price, invoice.currency)}</td>
                  <td className="py-2.5 pr-3 text-right text-[var(--foreground-secondary)]">{l.tax_rate}</td>
                  <td className="py-2.5 pr-3 text-right text-[var(--foreground-secondary)]">{formatMoney(l.tax_amount, invoice.currency)}</td>
                  <td className="py-2.5 text-right font-medium text-[var(--foreground)]">{formatMoney(l.amount, invoice.currency)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <div className="grid gap-5 lg:grid-cols-2">
        {/* Adjustments */}
        <Card>
          <h3 className="mb-3 text-sm font-semibold text-[var(--foreground-secondary)]">Concessions</h3>
          {invoice.adjustments.length === 0 ? (
            <p className="py-4 text-center text-sm text-[var(--muted)]">No concessions applied.</p>
          ) : (
            <div className="space-y-2">
              {invoice.adjustments.map((a) => (
                <div key={a.id} className="flex items-center justify-between rounded-xl border border-[var(--border)] px-3 py-2 text-sm">
                  <div>
                    <div className="font-medium capitalize text-[var(--foreground)]">{a.kind}</div>
                    {a.note ? <div className="text-xs text-[var(--muted)]">{a.note}</div> : null}
                  </div>
                  <div className="font-semibold text-[var(--foreground)]">− {formatMoney(a.amount, invoice.currency)}</div>
                </div>
              ))}
            </div>
          )}
        </Card>

        {/* Payments */}
        <Card>
          <h3 className="mb-3 text-sm font-semibold text-[var(--foreground-secondary)]">Payments</h3>
          {invoice.payments.length === 0 ? (
            <p className="py-4 text-center text-sm text-[var(--muted)]">No payments recorded.</p>
          ) : (
            <div className="space-y-2">
              {invoice.payments.map((p) => (
                <div key={p.id} className="flex items-center justify-between rounded-xl border border-[var(--border)] px-3 py-2 text-sm">
                  <div>
                    <div className="font-medium text-[var(--foreground)]">{p.receipt_number || "—"}</div>
                    <div className="text-xs text-[var(--muted)]">
                      {p.method.replace(/_/g, " ")} · {p.received_at ? new Date(p.received_at).toLocaleDateString() : "—"}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <StatusBadge status={p.status} />
                    <span className="font-semibold text-[var(--foreground)]">{formatMoney(p.amount, invoice.currency)}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      {/* Totals */}
      <Card>
        <div className="ml-auto max-w-sm space-y-1.5 text-sm">
          <div className="flex justify-between text-[var(--foreground-secondary)]">
            <span>Subtotal</span>
            <span>{formatMoney(invoice.subtotal, invoice.currency)}</span>
          </div>
          <div className="flex justify-between text-[var(--foreground-secondary)]">
            <span>Tax</span>
            <span>{formatMoney(invoice.tax_total, invoice.currency)}</span>
          </div>
          <div className="flex justify-between text-[var(--foreground-secondary)]">
            <span>Discounts</span>
            <span>− {formatMoney(invoice.discount_total, invoice.currency)}</span>
          </div>
          <div className="flex justify-between text-[var(--foreground-secondary)]">
            <span>Scholarships</span>
            <span>− {formatMoney(invoice.scholarship_total, invoice.currency)}</span>
          </div>
          <div className="flex justify-between border-t border-[var(--border)] pt-1.5 font-semibold text-[var(--foreground)]">
            <span>Total</span>
            <span>{formatMoney(invoice.total, invoice.currency)}</span>
          </div>
          <div className="flex justify-between text-[var(--foreground-secondary)]">
            <span>Paid</span>
            <span>{formatMoney(invoice.paid_amount, invoice.currency)}</span>
          </div>
          <div className="flex justify-between text-base font-bold text-[var(--foreground)]">
            <span>Balance</span>
            <span>{formatMoney(invoice.balance, invoice.currency)}</span>
          </div>
        </div>
      </Card>

      {/* Record payment modal */}
      <Modal open={paying} title={`Record payment · ${invoice.number}`} onClose={() => setPaying(false)}>
        <div className="space-y-3">
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
            <Button variant="ghost" onClick={() => setPaying(false)}>
              Cancel
            </Button>
            <Button loading={busy} onClick={recordPayment}>
              Record payment
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
