"use client";

import { InventoryShell } from "@/features/inventory/components/primitives";
import { StockMovements } from "@/features/inventory/components/StockMovements";

export default function MovementsPage() {
  return (
    <InventoryShell title="Movements" description="Every stock in/out movement">
      <StockMovements />
    </InventoryShell>
  );
}
