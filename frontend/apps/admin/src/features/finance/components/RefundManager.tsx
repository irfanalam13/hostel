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
  useToast,
} from "@hostel/ui";
import { Check, Plus, Send, X } from "lucide-react";

import { financeApi } from "../api/finance.api";
import { PAYMENT_METHODS, REFUND_TYPES } from "../constants";
import type { Refund, RefundStatus, RefundType } from "../types/finance.types";
import { ResidentPicker } from "./ResidentPicker";
import { StatusBadge, formatMoney } from "./primitives";

const STATUS_FILTERS: { value: RefundStatus | ""; label: string }[] = [
  { value: "", label: "All statuses" },
  { value: "requested", label: "Requested" },
  { value: "approved", label: "Approved" },
  { value: "rejected", label: "Rejected" },
  { value: "processed", label: "Processed" },
];

type RefundForm = {
  refund_type: RefundType;
  resident: string;
  amount: string;
  method: Refund["method"];
  reason: string;
  note: string;
};

const emptyRefund: RefundForm = {
  refund_type: "security_deposit",
  resident: "",
  amount: "0",
  method: "cash",
  reason: "",
  note: "",
};

export function RefundManager() {
  const toast = useToast();

  const [rows, setRows] = useState<Refund[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<RefundStatus | "">("");

  const [open, setOpen] = useState(false);
  const [form, setForm] = useState<RefundForm>(emptyRefund);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows(await financeApi.refunds.list({ search, status: statusFilter || undefined }));
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

  const set = (patch: Partial<RefundForm>) => setForm((f) => ({ ...f, ...patch }));

  const submit = async () => {
    if (!form.reason.trim()) {
      toast.error("A reason is required.");
      return;
    }
    setBusy(true);
    try {
      await financeApi.refunds.create({
        refund_type: form.refund_type,
        resident: form.resident || undefined,
        amount: form.amount || "0",
        method: form.method,
        reason: form.reason.trim(),
        note: form.note || undefined,
      });
      toast.success("Refund requested.");
      setOpen(false);
      setForm(emptyRefund);
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

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-2">
        <div className="flex-1 min-w-[200px]">
          <Input
            label="Search"
            placeholder="Reason or resident…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <Select
          label="Status"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as RefundStatus | "")}
          options={STATUS_FILTERS}
        />
        <Button onClick={() => { setForm(emptyRefund); setOpen(true); }}>
          <Plus className="h-4 w-4" /> Request refund
        </Button>
      </div>

      {loading ? (
        <div className="text-sm text-[var(--muted)]">Loading…</div>
      ) : rows.length === 0 ? (
        <EmptyState title="No refunds" description="Raise, approve and process resident refunds here." />
      ) : (
        <Table>
          <thead>
            <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
              <th className="px-4 py-3 font-medium">Type</th>
              <th className="px-4 py-3 font-medium">Resident</th>
              <th className="px-4 py-3 font-medium">Reason</th>
              <th className="px-4 py-3 font-medium text-right">Amount</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} className="border-b border-[var(--border)] last:border-0">
                <td className="px-4 py-3 capitalize text-[var(--foreground)]">{r.refund_type.replace(/_/g, " ")}</td>
                <td className="px-4 py-3 text-[var(--foreground-secondary)]">{r.resident_name || "—"}</td>
                <td className="px-4 py-3 text-[var(--foreground-secondary)]">{r.reason}</td>
                <td className="px-4 py-3 text-right text-[var(--foreground)]">{formatMoney(r.amount)}</td>
                <td className="px-4 py-3"><StatusBadge status={r.status} /></td>
                <td className="px-4 py-3">
                  <div className="flex items-center justify-end gap-1">
                    {r.status === "requested" ? (
                      <>
                        <Button variant="ghost" size="sm" title="Approve" onClick={() => act(() => financeApi.refunds.approve(r.id), "Refund approved.")}>
                          <Check className="h-4 w-4 text-[var(--success)]" />
                        </Button>
                        <Button variant="ghost" size="sm" title="Reject" onClick={() => act(() => financeApi.refunds.reject(r.id), "Refund rejected.")}>
                          <X className="h-4 w-4 text-[var(--error)]" />
                        </Button>
                      </>
                    ) : null}
                    {r.status === "approved" ? (
                      <Button variant="ghost" size="sm" title="Process" onClick={() => act(() => financeApi.refunds.process(r.id), "Refund processed.")}>
                        <Send className="h-4 w-4 text-[var(--accent)]" /> Process
                      </Button>
                    ) : null}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      <Modal open={open} title="Request refund" onClose={() => setOpen(false)}>
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <Select label="Refund type" value={form.refund_type} onChange={(e) => set({ refund_type: e.target.value as RefundType })} options={REFUND_TYPES} />
            <Select label="Method" value={form.method} onChange={(e) => set({ method: e.target.value as Refund["method"] })} options={PAYMENT_METHODS} />
          </div>
          <ResidentPicker label="Resident (optional)" value={form.resident} onChange={(id) => set({ resident: id })} />
          <Input label="Amount" type="number" value={form.amount} onChange={(e) => set({ amount: e.target.value })} />
          <Textarea label="Reason" value={form.reason} onChange={(e) => set({ reason: e.target.value })} />
          <Textarea label="Note (optional)" value={form.note} onChange={(e) => set({ note: e.target.value })} />
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button loading={busy} onClick={submit}>
              Request
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
