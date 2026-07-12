"use client";

import { FinanceShell } from "@/features/finance/components/primitives";
import { IncomeManager } from "@/features/finance/components/IncomeManager";

export default function IncomePage() {
  return (
    <FinanceShell title="Income" description="Log ancillary and non-fee income.">
      <IncomeManager />
    </FinanceShell>
  );
}
