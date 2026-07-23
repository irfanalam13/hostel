"use client";

import React, { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Button, Table, useToast } from "@hostel/ui";

import { inventoryApi } from "../api/inventory.api";
import type { Item, StockLevel, StockMovement } from "../types/inventory.types";
import { ReadField, StatusBadge, cardClass, formatMoney, formatQty } from "./primitives";

export function ItemDetail({ itemId }: { itemId: string }) {
  const toast = useToast();
  const router = useRouter();

  const [item, setItem] = useState<Item | null>(null);
  const [levels, setLevels] = useState<StockLevel[]>([]);
  const [movements, setMovements] = useState<StockMovement[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [it, lv, mv] = await Promise.all([
        inventoryApi.items.retrieve(itemId),
        inventoryApi.stockLevels.list({ item: itemId }),
        inventoryApi.items.movements(itemId),
      ]);
      setItem(it);
      setLevels(lv);
      setMovements(mv);
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [itemId, toast]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) return <div className="text-sm text-[var(--muted)]">Loading…</div>;
  if (!item) return <div className="text-sm text-[var(--muted)]">Item not found.</div>;

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3">
        <h2 className="text-lg font-semibold text-[var(--foreground)]">{item.name}</h2>
        <span className="font-mono text-xs text-[var(--muted)]">{item.item_code}</span>
      </div>

      <div className={`${cardClass} grid grid-cols-2 gap-4 sm:grid-cols-4`}>
        <ReadField label="Category" value={item.category_name} />
        <ReadField label="Type" value={item.item_type.replace(/_/g, " ")} />
        <ReadField label="On hand" value={formatQty(item.on_hand)} />
        <ReadField label="Reorder level" value={formatQty(item.reorder_level)} />
        <ReadField label="Purchase price" value={formatMoney(item.purchase_price)} />
        <ReadField label="Average cost" value={formatMoney(item.average_cost)} />
        <ReadField label="Selling price" value={formatMoney(item.selling_price)} />
        <ReadField label="Brand" value={item.brand_name} />
      </div>

      <div className={cardClass}>
        <h3 className="mb-3 text-sm font-semibold text-[var(--foreground-secondary)]">Stock by warehouse</h3>
        {levels.length === 0 ? (
          <p className="py-4 text-center text-sm text-[var(--muted)]">No stock on hand.</p>
        ) : (
          <Table>
            <thead>
              <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
                <th className="px-4 py-3 font-medium">Warehouse</th>
                <th className="px-4 py-3 font-medium text-right">On hand</th>
                <th className="px-4 py-3 font-medium text-right">Available</th>
              </tr>
            </thead>
            <tbody>
              {levels.map((l) => (
                <tr key={l.id} className="border-b border-[var(--border)] last:border-0">
                  <td className="px-4 py-3 text-[var(--foreground)]">{l.warehouse_name}</td>
                  <td className="px-4 py-3 text-right text-[var(--foreground)]">{formatQty(l.quantity_on_hand)}</td>
                  <td className="px-4 py-3 text-right text-[var(--foreground-secondary)]">{formatQty(l.quantity_available)}</td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </div>

      <div className={cardClass}>
        <h3 className="mb-3 text-sm font-semibold text-[var(--foreground-secondary)]">Recent movements</h3>
        {movements.length === 0 ? (
          <p className="py-4 text-center text-sm text-[var(--muted)]">No movements yet.</p>
        ) : (
          <Table>
            <thead>
              <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
                <th className="px-4 py-3 font-medium">Ref</th>
                <th className="px-4 py-3 font-medium">Type</th>
                <th className="px-4 py-3 font-medium text-right">Qty</th>
                <th className="px-4 py-3 font-medium text-right">When</th>
              </tr>
            </thead>
            <tbody>
              {movements.slice(0, 20).map((m) => (
                <tr key={m.id} className="border-b border-[var(--border)] last:border-0">
                  <td className="px-4 py-3 font-mono text-xs text-[var(--foreground-secondary)]">{m.reference}</td>
                  <td className="px-4 py-3"><StatusBadge status={m.direction} label={m.movement_type.replace(/_/g, " ")} /></td>
                  <td className="px-4 py-3 text-right font-semibold" style={{ color: m.direction === "in" ? "var(--success)" : "var(--error)" }}>
                    {m.direction === "in" ? "+" : "−"}{formatQty(m.quantity)}
                  </td>
                  <td className="px-4 py-3 text-right text-[var(--muted)]">{new Date(m.occurred_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </div>

      <div>
        <Button variant="ghost" size="sm" onClick={() => router.push("/inventory/items")}>← Back to items</Button>
      </div>
    </div>
  );
}
