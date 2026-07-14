"use client";

import { InventoryShell } from "@/features/inventory/components/primitives";
import { WarehouseManager } from "@/features/inventory/components/WarehouseManager";

export default function WarehousesPage() {
  return (
    <InventoryShell title="Warehouses" description="Warehouses and storage locations">
      <WarehouseManager />
    </InventoryShell>
  );
}
