"use client";

import { AccountingShell } from "@/features/accounting/components/primitives";
import { Banking } from "@/features/accounting/components/Banking";

export default function BankingPage() {
  return (
    <AccountingShell title="Banking" description="Bank accounts and statement reconciliation.">
      <Banking />
    </AccountingShell>
  );
}
