"use client";

import React, { useEffect, useState } from "react";
import { Button, Table, useToast } from "@hostel/ui";
import { Download, FileSpreadsheet } from "lucide-react";

import { inventoryApi } from "../api/inventory.api";
import { cardClass, formatMoney } from "./primitives";

type ValuationRow = Record<string, string>;

export function InventoryReports() {
  const toast = useToast();
  const [valuation, setValuation] = useState<{ items: ValuationRow[]; total_value: string } | null>(null);
  const [lowStock, setLowStock] = useState<ValuationRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const [v, ls] = await Promise.all([inventoryApi.reports.valuation(), inventoryApi.reports.lowStock()]);
        setValuation(v);
        setLowStock(ls.items);
      } catch (e) {
        toast.error((e as Error).message);
      } finally {
        setLoading(false);
      }
    })();
  }, [toast]);

  const download = async (fn: () => Promise<void>) => {
    try {
      await fn();
    } catch (e) {
      toast.error((e as Error).message, "Export failed");
    }
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap gap-2">
        <Button variant="secondary" size="sm" onClick={() => download(() => inventoryApi.reports.exportCsv("stock-summary"))}>
          <Download className="h-4 w-4" /> Stock summary (CSV)
        </Button>
        <Button variant="secondary" size="sm" onClick={() => download(() => inventoryApi.reports.exportXlsx("stock-summary"))}>
          <FileSpreadsheet className="h-4 w-4" /> Stock summary (Excel)
        </Button>
      </div>

      {loading ? (
        <div className="text-sm text-[var(--muted)]">Loading…</div>
      ) : (
        <>
          <div className={cardClass}>
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-[var(--foreground-secondary)]">Inventory Valuation</h3>
              <span className="text-sm font-semibold text-[var(--foreground)]">
                Total: {formatMoney(valuation?.total_value)}
              </span>
            </div>
            {!valuation || valuation.items.length === 0 ? (
              <p className="py-4 text-center text-sm text-[var(--muted)]">No items to value.</p>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <thead>
                    <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
                      <th className="px-4 py-3 font-medium">Code</th>
                      <th className="px-4 py-3 font-medium">Item</th>
                      <th className="px-4 py-3 font-medium text-right">On hand</th>
                      <th className="px-4 py-3 font-medium text-right">Avg cost</th>
                      <th className="px-4 py-3 font-medium text-right">Value</th>
                    </tr>
                  </thead>
                  <tbody>
                    {valuation.items.map((r) => (
                      <tr key={r.item_code} className="border-b border-[var(--border)] last:border-0">
                        <td className="px-4 py-3 font-mono text-xs text-[var(--foreground-secondary)]">{r.item_code}</td>
                        <td className="px-4 py-3 text-[var(--foreground)]">{r.name}</td>
                        <td className="px-4 py-3 text-right text-[var(--foreground-secondary)]">{r.on_hand}</td>
                        <td className="px-4 py-3 text-right text-[var(--foreground-secondary)]">{formatMoney(r.average_cost)}</td>
                        <td className="px-4 py-3 text-right font-semibold text-[var(--foreground)]">{formatMoney(r.value)}</td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              </div>
            )}
          </div>

          <div className={cardClass}>
            <h3 className="mb-3 text-sm font-semibold text-[var(--foreground-secondary)]">Low Stock</h3>
            {lowStock.length === 0 ? (
              <p className="py-4 text-center text-sm text-[var(--muted)]">Everything is above reorder level. 🎉</p>
            ) : (
              <Table>
                <thead>
                  <tr className="border-b border-[var(--border)] text-left text-[var(--muted)]">
                    <th className="px-4 py-3 font-medium">Code</th>
                    <th className="px-4 py-3 font-medium">Item</th>
                    <th className="px-4 py-3 font-medium text-right">On hand</th>
                    <th className="px-4 py-3 font-medium text-right">Reorder level</th>
                  </tr>
                </thead>
                <tbody>
                  {lowStock.map((r) => (
                    <tr key={r.item_code} className="border-b border-[var(--border)] last:border-0">
                      <td className="px-4 py-3 font-mono text-xs text-[var(--foreground-secondary)]">{r.item_code}</td>
                      <td className="px-4 py-3 text-[var(--foreground)]">{r.name}</td>
                      <td className="px-4 py-3 text-right font-semibold" style={{ color: "var(--warning)" }}>{r.on_hand}</td>
                      <td className="px-4 py-3 text-right text-[var(--foreground-secondary)]">{r.reorder_level}</td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            )}
          </div>
        </>
      )}
    </div>
  );
}
