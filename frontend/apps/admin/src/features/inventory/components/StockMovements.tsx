"use client";

import React, { useCallback, useEffect, useState } from "react";
import { EmptyState, Select, Table, useToast } from "@hostel/ui";

import { inventoryApi } from "../api/inventory.api";
import { MOVEMENT_TYPES } from "../constants";
import type { StockMovement } from "../types/inventory.types";
import { StatusBadge, formatMoney, formatQty } from "./primitives";

export function StockMovements() {
  const toast = useToast();
  const [rows, setRows] = useState<StockMovement[]>([]);
  const [type, setType] = useState("");
  const [direction, setDirection] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRows(
        await inventoryApi.movements.list({
          movement_type: type || undefined,
          direction: direction || undefined,
          ordering: "-occurred_at",
        }),
      );
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [type, direction, toast]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-2">
        <Select
          label="Type"
          value={type}
          onChange={(e) => setType(e.target.value)}
          options={[{ value: "", label: "All types" }, ...MOVEMENT_TYPES]}
        />
        <Select
          label="Direction"
          value={direction}
          onChange={(e) => setDirection(e.target.value)}
          options={[
            { value: "", label: "All" },
            { value: "in", label: "In" },
            { value: "out", label: "Out" },
          ]}
        />
      </div>

      {loading ? (
        <div className="text-sm text-[var(--muted)]">Loading…</div>
      ) : rows.length === 0 ? (
        <EmptyState title="No movements" description="Stock movements appear here as goods flow in and out." />
      ) : (
        <Table>
          <thead>
            <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
              <th className="px-4 py-3 font-medium">Ref</th>
              <th className="px-4 py-3 font-medium">Item</th>
              <th className="px-4 py-3 font-medium">Warehouse</th>
              <th className="px-4 py-3 font-medium">Type</th>
              <th className="px-4 py-3 font-medium text-right">Qty</th>
              <th className="px-4 py-3 font-medium text-right">Unit cost</th>
              <th className="px-4 py-3 font-medium text-right">When</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((m) => (
              <tr key={m.id} className="border-b border-[var(--border)] last:border-0">
                <td className="px-4 py-3 font-mono text-xs text-[var(--foreground-secondary)]">{m.reference}</td>
                <td className="px-4 py-3 text-[var(--foreground)]">{m.item_name}</td>
                <td className="px-4 py-3 text-[var(--foreground-secondary)]">{m.warehouse_name}</td>
                <td className="px-4 py-3"><StatusBadge status={m.direction} label={m.movement_type.replace(/_/g, " ")} /></td>
                <td className="px-4 py-3 text-right font-semibold" style={{ color: m.direction === "in" ? "var(--success)" : "var(--error)" }}>
                  {m.direction === "in" ? "+" : "−"}{formatQty(m.quantity)}
                </td>
                <td className="px-4 py-3 text-right text-[var(--foreground-secondary)]">{formatMoney(m.unit_cost)}</td>
                <td className="px-4 py-3 text-right text-[var(--muted)]">{new Date(m.occurred_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </div>
  );
}
