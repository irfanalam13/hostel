"use client";

import { AccountingShell } from "@/features/accounting/components/primitives";
import { Statements } from "@/features/accounting/components/Statements";

export default function StatementsPage() {
  return (
    <AccountingShell title="Statements" description="Trial balance, P&L, balance sheet, cash flow and register.">
      <Statements />
    </AccountingShell>
  );
}
