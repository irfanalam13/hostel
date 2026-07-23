"use client";

import { InventoryShell } from "@/features/inventory/components/primitives";
import { VendorList } from "@/features/inventory/components/VendorList";

export default function VendorsPage() {
  return (
    <InventoryShell title="Vendors" description="Suppliers and vendor management">
      <VendorList />
    </InventoryShell>
  );
}
