"use client";

import { FinanceShell } from "@/features/finance/components/primitives";
import { FinanceOverview } from "@/features/finance/components/FinanceOverview";

export default function FinancePage() {
  return (
    <FinanceShell title="Overview" description="Revenue, expenses and cash-flow at a glance.">
      <FinanceOverview />
    </FinanceShell>
  );
}
