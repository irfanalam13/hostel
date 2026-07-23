"use client";

import { InventoryShell } from "@/features/inventory/components/primitives";
import { StockLevels } from "@/features/inventory/components/StockLevels";

export default function StockPage() {
  return (
    <InventoryShell title="Stock" description="On-hand levels across warehouses">
      <StockLevels />
    </InventoryShell>
  );
}
