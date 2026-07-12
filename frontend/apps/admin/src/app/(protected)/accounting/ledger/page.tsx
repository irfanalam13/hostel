"use client";

import { AccountingShell } from "@/features/accounting/components/primitives";
import { LedgerView } from "@/features/accounting/components/LedgerView";

export default function LedgerPage() {
  return (
    <AccountingShell title="Ledger" description="General ledger with running balances.">
      <LedgerView />
    </AccountingShell>
  );
}
