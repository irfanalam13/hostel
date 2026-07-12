"use client";

import { AccountingShell } from "@/features/accounting/components/primitives";
import { FiscalYears } from "@/features/accounting/components/FiscalYears";

export default function FiscalYearsPage() {
  return (
    <AccountingShell title="Fiscal Years" description="Periods, opening balances and year-end close.">
      <FiscalYears />
    </AccountingShell>
  );
}
