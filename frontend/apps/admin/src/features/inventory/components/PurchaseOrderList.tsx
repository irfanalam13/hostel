"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Button, EmptyState, Input, Modal, Select, Table, useToast } from "@hostel/ui";
import { Eye, Plus, Trash2 } from "lucide-react";

import { inventoryApi } from "../api/inventory.api";
import { PO_STATUS_LABELS } from "../constants";
import type { Item, PurchaseOrder, Vendor, Warehouse } from "../types/inventory.types";
import { StatusBadge, formatMoney } from "./primitives";

type DraftLine = { item: string; ordered_quantity: string; unit_price: string; tax_rate: string };

export function PurchaseOrderList() {
  const toast = useToast();

  const [rows, setRows] = useState<PurchaseOrder[]>([]);
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [items, setItems] = useState<Item[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");

  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [vendor, setVendor] = useState("");
  const [warehouse, setWarehouse] = useState("");
  const [lines, setLines] = useState<DraftLine[]>([{ item: "", ordered_quantity: "1", unit_price: "0", tax_rate: "0" }]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows(await inventoryApi.purchaseOrders.list({ status: statusFilter || undefined, ordering: "-order_date" }));
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [statusFilter, toast]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    inventoryApi.vendors.list().then(setVendors).catch(() => {});
    inventoryApi.warehouses.list().then(setWarehouses).catch(() => {});
    inventoryApi.items.list().then(setItems).catch(() => {});
  }, []);

  const setLine = (i: number, patch: Partial<DraftLine>) =>
    setLines((ls) => ls.map((l, idx) => (idx === i ? { ...l, ...patch } : l)));
  const addLine = () => setLines((ls) => [...ls, { item: "", ordered_quantity: "1", unit_price: "0", tax_rate: "0" }]);
  const removeLine = (i: number) => setLines((ls) => ls.filter((_, idx) => idx !== i));

  const startCreate = () => {
    setVendor(vendors[0]?.id ?? "");
    setWarehouse(warehouses.find((w) => w.is_default)?.id ?? warehouses[0]?.id ?? "");
    setLines([{ item: items[0]?.id ?? "", ordered_quantity: "1", unit_price: "0", tax_rate: "0" }]);
    setOpen(true);
  };

  const submit = async () => {
    if (!vendor) return toast.error("Select a vendor.");
    const validLines = lines.filter((l) => l.item && Number(l.ordered_quantity) > 0);
    if (validLines.length === 0) return toast.error("Add at least one line.");
    setBusy(true);
    try {
      await inventoryApi.purchaseOrders.create({
        vendor,
        warehouse: warehouse || null,
        lines: validLines,
      });
      toast.success("Purchase order created.");
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
        <Select
          label="Status"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          options={[{ value: "", label: "All statuses" }, ...Object.entries(PO_STATUS_LABELS).map(([value, label]) => ({ value, label }))]}
        />
        <div className="flex-1" />
        <Button onClick={startCreate}>
          <Plus className="h-4 w-4" /> New purchase order
        </Button>
      </div>

      {loading ? (
        <div className="text-sm text-[var(--muted)]">Loading…</div>
      ) : rows.length === 0 ? (
        <EmptyState title="No purchase orders" description="Raise a PO to procure stock from a vendor." />
      ) : (
        <Table>
          <thead>
            <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
              <th className="px-4 py-3 font-medium">PO #</th>
              <th className="px-4 py-3 font-medium">Vendor</th>
              <th className="px-4 py-3 font-medium">Date</th>
              <th className="px-4 py-3 font-medium text-right">Total</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((po) => (
              <tr key={po.id} className="border-b border-[var(--border)] last:border-0">
                <td className="px-4 py-3 font-mono text-xs text-[var(--foreground)]">{po.po_number}</td>
                <td className="px-4 py-3 text-[var(--foreground-secondary)]">{po.vendor_name}</td>
                <td className="px-4 py-3 text-[var(--foreground-secondary)]">{po.order_date}</td>
                <td className="px-4 py-3 text-right font-semibold text-[var(--foreground)]">{formatMoney(po.total)}</td>
                <td className="px-4 py-3"><StatusBadge status={po.status} /></td>
                <td className="px-4 py-3 text-right">
                  <Link href={`/inventory/purchase-orders/${po.id}`}>
                    <Button variant="ghost" size="sm"><Eye className="h-4 w-4" /></Button>
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      <Modal open={open} title="New purchase order" onClose={() => setOpen(false)}>
        <div className="max-h-[74vh] space-y-3 overflow-y-auto pr-1">
          <div className="grid grid-cols-2 gap-3">
            <Select label="Vendor" value={vendor} onChange={(e) => setVendor(e.target.value)}>
              <option value="">Select…</option>
              {vendors.map((v) => <option key={v.id} value={v.id}>{v.company_name}</option>)}
            </Select>
            <Select label="Warehouse" value={warehouse} onChange={(e) => setWarehouse(e.target.value)}>
              <option value="">Default</option>
              {warehouses.map((w) => <option key={w.id} value={w.id}>{w.name}</option>)}
            </Select>
          </div>

          <div className="space-y-2">
            <div className="text-sm font-medium text-[var(--foreground-secondary)]">Lines</div>
            {lines.map((l, i) => (
              <div key={i} className="grid grid-cols-[1fr_70px_90px_70px_32px] items-end gap-2">
                <Select value={l.item} onChange={(e) => setLine(i, { item: e.target.value })}>
                  <option value="">Item…</option>
                  {items.map((it) => <option key={it.id} value={it.id}>{it.name}</option>)}
                </Select>
                <Input type="number" placeholder="Qty" value={l.ordered_quantity} onChange={(e) => setLine(i, { ordered_quantity: e.target.value })} />
                <Input type="number" placeholder="Price" value={l.unit_price} onChange={(e) => setLine(i, { unit_price: e.target.value })} />
                <Input type="number" placeholder="Tax%" value={l.tax_rate} onChange={(e) => setLine(i, { tax_rate: e.target.value })} />
                <Button variant="ghost" size="sm" onClick={() => removeLine(i)} disabled={lines.length === 1}>
                  <Trash2 className="h-4 w-4 text-[var(--error)]" />
                </Button>
              </div>
            ))}
            <Button variant="ghost" size="sm" onClick={addLine}><Plus className="h-4 w-4" /> Add line</Button>
          </div>

          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
            <Button loading={busy} onClick={submit}>Create</Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
