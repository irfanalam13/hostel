"use client";

import { AccountingShell } from "@/features/accounting/components/primitives";
import { AccountingOverview } from "@/features/accounting/components/AccountingOverview";

export default function AccountingPage() {
  return (
    <AccountingShell title="Overview" description="Financial position and key ledger metrics at a glance.">
      <AccountingOverview />
    </AccountingShell>
  );
}
