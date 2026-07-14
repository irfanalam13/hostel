"use client";

import { InventoryShell } from "@/features/inventory/components/primitives";
import { InventoryReports } from "@/features/inventory/components/InventoryReports";

export default function ReportsPage() {
  return (
    <InventoryShell title="Reports" description="Valuation, low-stock and exports">
      <InventoryReports />
    </InventoryShell>
  );
}
