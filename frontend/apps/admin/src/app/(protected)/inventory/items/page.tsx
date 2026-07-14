"use client";

import { InventoryShell } from "@/features/inventory/components/primitives";
import { ItemList } from "@/features/inventory/components/ItemList";

export default function ItemsPage() {
  return (
    <InventoryShell title="Items" description="The item master catalog">
      <ItemList />
    </InventoryShell>
  );
}
