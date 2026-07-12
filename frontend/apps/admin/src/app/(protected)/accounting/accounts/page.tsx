"use client";

import { AccountingShell } from "@/features/accounting/components/primitives";
import { ChartOfAccounts } from "@/features/accounting/components/ChartOfAccounts";

export default function AccountsPage() {
  return (
    <AccountingShell title="Chart of Accounts" description="Ledger accounts grouped by type.">
      <ChartOfAccounts />
    </AccountingShell>
  );
}
