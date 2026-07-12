"use client";

import { FinanceShell } from "@/features/finance/components/primitives";
import { FeeManager } from "@/features/finance/components/FeeManager";

export default function FeesPage() {
  return (
    <FinanceShell title="Fees" description="Fee categories, structures and resident assignments.">
      <FeeManager />
    </FinanceShell>
  );
}
