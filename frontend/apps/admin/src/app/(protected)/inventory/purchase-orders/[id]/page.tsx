"use client";

import { useParams } from "next/navigation";

import { InventoryShell } from "@/features/inventory/components/primitives";
import { PurchaseOrderDetail } from "@/features/inventory/components/PurchaseOrderDetail";

export default function PurchaseOrderDetailPage() {
  const params = useParams();
  const id = Array.isArray(params?.id) ? params.id[0] : (params?.id as string);
  return (
    <InventoryShell title="Purchase Order" description="Approve, receive and track a purchase order">
      <PurchaseOrderDetail poId={id} />
    </InventoryShell>
  );
}
