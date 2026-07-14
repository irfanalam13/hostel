"use client";

import { InventoryShell } from "@/features/inventory/components/primitives";
import { AssetList } from "@/features/inventory/components/AssetList";

export default function AssetsPage() {
  return (
    <InventoryShell title="Assets" description="Asset register and lifecycle">
      <AssetList />
    </InventoryShell>
  );
}
