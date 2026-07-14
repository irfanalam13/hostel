"use client";

import { InventoryShell } from "@/features/inventory/components/primitives";
import { PurchaseOrderList } from "@/features/inventory/components/PurchaseOrderList";

export default function PurchaseOrdersPage() {
  return (
    <InventoryShell title="Purchase Orders" description="Procurement and goods receipt">
      <PurchaseOrderList />
    </InventoryShell>
  );
}
