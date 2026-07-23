"use client";

import { AccountingShell } from "@/features/accounting/components/primitives";
import { Budgets } from "@/features/accounting/components/Budgets";

export default function BudgetsPage() {
  return (
    <AccountingShell title="Budgets" description="Plan and approve account budgets.">
      <Budgets />
    </AccountingShell>
  );
}
