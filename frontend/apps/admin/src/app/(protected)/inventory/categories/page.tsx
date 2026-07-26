"use client";

import { InventoryShell } from "@/features/inventory/components/primitives";
import { CategoryManager } from "@/features/inventory/components/CategoryManager";

export default function CatalogPage() {
  return (
    <InventoryShell title="Catalog" description="Categories, brands and units of measure">
      <CategoryManager />
    </InventoryShell>
  );
}
