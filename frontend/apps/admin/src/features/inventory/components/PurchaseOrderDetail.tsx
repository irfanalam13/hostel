"use client";

import React, { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Button, Input, Modal, Table, useConfirm, useToast } from "@hostel/ui";
import { Ban, CheckCircle2, PackageCheck, Send } from "lucide-react";

import { inventoryApi } from "../api/inventory.api";
import type { PurchaseOrder } from "../types/inventory.types";
import { ReadField, StatusBadge, cardClass, formatMoney, formatQty } from "./primitives";

export function PurchaseOrderDetail({ poId }: { poId: string }) {
  const toast = useToast();
  const confirm = useConfirm();
  const router = useRouter();

  const [po, setPo] = useState<PurchaseOrder | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const [receiveOpen, setReceiveOpen] = useState(false);
  const [receiveQty, setReceiveQty] = useState<Record<string, string>>({});

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setPo(await inventoryApi.purchaseOrders.retrieve(poId));
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [poId, toast]);

  useEffect(() => {
    load();
  }, [load]);

  const act = async (fn: () => Promise<unknown>, ok: string) => {
    setBusy(true);
    try {
      await fn();
      toast.success(ok);
      await load();
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const openReceive = () => {
    if (!po) return;
    const seed: Record<string, string> = {};
    for (const l of po.lines) {
      seed[l.id] = l.outstanding_quantity;
    }
    setReceiveQty(seed);
    setReceiveOpen(true);
  };

  const submitReceive = async () => {
    if (!po) return;
    const receiveLines = po.lines
      .filter((l) => Number(receiveQty[l.id] || "0") > 0)
      .map((l) => ({ item: l.item, po_line: l.id, quantity: receiveQty[l.id], unit_cost: l.unit_price }));
    if (receiveLines.length === 0) return toast.error("Enter a quantity to receive.");
    setBusy(true);
    try {
      await inventoryApi.purchaseOrders.receive(po.id, { lines: receiveLines });
      toast.success("Goods received.");
      setReceiveOpen(false);
      await load();
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  if (loading) return <div className="text-sm text-[var(--muted)]">Loading…</div>;
  if (!po) return <div className="text-sm text-[var(--muted)]">Purchase order not found.</div>;

  const canEdit = po.status === "draft" || po.status === "pending_approval";
  const canApprove = po.status === "draft" || po.status === "pending_approval";
  const canReceive = ["approved", "ordered", "partially_received"].includes(po.status);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <h2 className="font-mono text-lg font-semibold text-[var(--foreground)]">{po.po_number}</h2>
          <StatusBadge status={po.status} />
        </div>
        <div className="flex flex-wrap gap-2">
          {po.status === "draft" && (
            <Button variant="secondary" size="sm" loading={busy} onClick={() => act(() => inventoryApi.purchaseOrders.submit(po.id), "Submitted for approval.")}>
              <Send className="h-4 w-4" /> Submit
            </Button>
          )}
          {canApprove && (
            <Button size="sm" loading={busy} onClick={() => act(() => inventoryApi.purchaseOrders.approve(po.id), "Approved.")}>
              <CheckCircle2 className="h-4 w-4" /> Approve
            </Button>
          )}
          {canReceive && (
            <Button size="sm" onClick={openReceive}>
              <PackageCheck className="h-4 w-4" /> Receive goods
            </Button>
          )}
          {po.status !== "cancelled" && po.status !== "fully_received" && (
            <Button variant="ghost" size="sm" onClick={async () => {
              const yes = await confirm({ title: "Cancel PO", message: `Cancel ${po.po_number}?`, danger: true, confirmText: "Cancel PO" });
              if (yes) await act(() => inventoryApi.purchaseOrders.cancel(po.id), "Cancelled.");
            }}>
              <Ban className="h-4 w-4 text-[var(--error)]" /> Cancel
            </Button>
          )}
        </div>
      </div>

      <div className={`${cardClass} grid grid-cols-2 gap-4 sm:grid-cols-4`}>
        <ReadField label="Vendor" value={po.vendor_name} />
        <ReadField label="Order date" value={po.order_date} />
        <ReadField label="Total" value={formatMoney(po.total)} />
        <ReadField label="Status" value={<StatusBadge status={po.status} />} />
      </div>

      <div className={cardClass}>
        <h3 className="mb-3 text-sm font-semibold text-[var(--foreground-secondary)]">Lines</h3>
        <Table>
          <thead>
            <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
              <th className="px-4 py-3 font-medium">Item</th>
              <th className="px-4 py-3 font-medium text-right">Ordered</th>
              <th className="px-4 py-3 font-medium text-right">Received</th>
              <th className="px-4 py-3 font-medium text-right">Unit price</th>
              <th className="px-4 py-3 font-medium text-right">Line total</th>
            </tr>
          </thead>
          <tbody>
            {po.lines.map((l) => (
              <tr key={l.id} className="border-b border-[var(--border)] last:border-0">
                <td className="px-4 py-3 text-[var(--foreground)]">{l.item_name}</td>
                <td className="px-4 py-3 text-right text-[var(--foreground-secondary)]">{formatQty(l.ordered_quantity)}</td>
                <td className="px-4 py-3 text-right text-[var(--foreground-secondary)]">{formatQty(l.received_quantity)}</td>
                <td className="px-4 py-3 text-right text-[var(--foreground-secondary)]">{formatMoney(l.unit_price)}</td>
                <td className="px-4 py-3 text-right font-semibold text-[var(--foreground)]">{formatMoney(l.line_total)}</td>
              </tr>
            ))}
          </tbody>
        </Table>
        {!canEdit && po.status !== "fully_received" && po.status !== "cancelled" ? null : null}
      </div>

      <Modal open={receiveOpen} title={`Receive goods — ${po.po_number}`} onClose={() => setReceiveOpen(false)}>
        <div className="max-h-[74vh] space-y-3 overflow-y-auto pr-1">
          <p className="text-sm text-[var(--muted)]">Enter the quantity received for each line.</p>
          {po.lines.map((l) => (
            <div key={l.id} className="flex items-center gap-3">
              <div className="flex-1">
                <div className="text-sm text-[var(--foreground)]">{l.item_name}</div>
                <div className="text-xs text-[var(--muted)]">Outstanding: {formatQty(l.outstanding_quantity)}</div>
              </div>
              <div className="w-28">
                <Input
                  type="number"
                  value={receiveQty[l.id] ?? "0"}
                  onChange={(e) => setReceiveQty((q) => ({ ...q, [l.id]: e.target.value }))}
                />
              </div>
            </div>
          ))}
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setReceiveOpen(false)}>Cancel</Button>
            <Button loading={busy} onClick={submitReceive}>Receive</Button>
          </div>
        </div>
      </Modal>

      <div>
        <Button variant="ghost" size="sm" onClick={() => router.push("/inventory/purchase-orders")}>← Back to purchase orders</Button>
      </div>
    </div>
  );
}
