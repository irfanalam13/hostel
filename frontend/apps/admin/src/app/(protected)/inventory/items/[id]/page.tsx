"use client";

import { useParams } from "next/navigation";

import { InventoryShell } from "@/features/inventory/components/primitives";
import { ItemDetail } from "@/features/inventory/components/ItemDetail";

export default function ItemDetailPage() {
  const params = useParams();
  const id = Array.isArray(params?.id) ? params.id[0] : (params?.id as string);
  return (
    <InventoryShell title="Item" description="Item details, stock and movement history">
      <ItemDetail itemId={id} />
    </InventoryShell>
  );
}
