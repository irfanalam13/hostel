"use client";

import { InventoryShell } from "@/features/inventory/components/primitives";
import { InventoryOverview } from "@/features/inventory/components/InventoryOverview";

export default function InventoryPage() {
  return (
    <InventoryShell title="Overview" description="Stock value, assets and procurement at a glance">
      <InventoryOverview />
    </InventoryShell>
  );
}
