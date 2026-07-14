"use client";

import { useParams } from "next/navigation";

import { InventoryShell } from "@/features/inventory/components/primitives";
import { AssetDetail } from "@/features/inventory/components/AssetDetail";

export default function AssetDetailPage() {
  const params = useParams();
  const id = Array.isArray(params?.id) ? params.id[0] : (params?.id as string);
  return (
    <InventoryShell title="Asset" description="Asset details, assignment and lifecycle">
      <AssetDetail assetId={id} />
    </InventoryShell>
  );
}
