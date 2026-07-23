"use client";

import React, { useCallback, useEffect, useState } from "react";
import { EmptyState, Input, Select, Table, useToast } from "@hostel/ui";

import { inventoryApi } from "../api/inventory.api";
import type { StockLevel, Warehouse } from "../types/inventory.types";
import { formatQty } from "./primitives";

export function StockLevels() {
  const toast = useToast();
  const [rows, setRows] = useState<StockLevel[]>([]);
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [warehouse, setWarehouse] = useState("");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows(await inventoryApi.stockLevels.list({ warehouse: warehouse || undefined }));
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [warehouse, toast]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    inventoryApi.warehouses.list().then(setWarehouses).catch(() => {});
  }, []);

  const filtered = rows.filter((r) =>
    !search || (r.item_name ?? "").toLowerCase().includes(search.toLowerCase()) ||
    (r.item_code ?? "").toLowerCase().includes(search.toLowerCase()),
  );

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-2">
        <div className="flex-1 min-w-[200px]">
          <Input label="Search" placeholder="Item name or code…" value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
        <Select label="Warehouse" value={warehouse} onChange={(e) => setWarehouse(e.target.value)}>
          <option value="">All warehouses</option>
          {warehouses.map((w) => <option key={w.id} value={w.id}>{w.name}</option>)}
        </Select>
      </div>

      {loading ? (
        <div className="text-sm text-[var(--muted)]">Loading…</div>
      ) : filtered.length === 0 ? (
        <EmptyState title="No stock" description="Receive goods or adjust stock to populate levels." />
      ) : (
        <Table>
          <thead>
            <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
              <th className="px-4 py-3 font-medium">Item</th>
              <th className="px-4 py-3 font-medium">Warehouse</th>
              <th className="px-4 py-3 font-medium text-right">On hand</th>
              <th className="px-4 py-3 font-medium text-right">Reserved</th>
              <th className="px-4 py-3 font-medium text-right">Allocated</th>
              <th className="px-4 py-3 font-medium text-right">Available</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((r) => (
              <tr key={r.id} className="border-b border-[var(--border)] last:border-0">
                <td className="px-4 py-3">
                  <div className="text-[var(--foreground)]">{r.item_name}</div>
                  <div className="font-mono text-xs text-[var(--muted)]">{r.item_code}</div>
                </td>
                <td className="px-4 py-3 text-[var(--foreground-secondary)]">{r.warehouse_name}</td>
                <td className="px-4 py-3 text-right font-semibold text-[var(--foreground)]">{formatQty(r.quantity_on_hand)}</td>
                <td className="px-4 py-3 text-right text-[var(--foreground-secondary)]">{formatQty(r.quantity_reserved)}</td>
                <td className="px-4 py-3 text-right text-[var(--foreground-secondary)]">{formatQty(r.quantity_allocated)}</td>
                <td className="px-4 py-3 text-right font-semibold text-[var(--foreground)]">{formatQty(r.quantity_available)}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </div>
  );
}
