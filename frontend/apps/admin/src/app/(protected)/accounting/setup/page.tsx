"use client";

import { AccountingShell } from "@/features/accounting/components/primitives";
import { Setup } from "@/features/accounting/components/Setup";

export default function SetupPage() {
  return (
    <AccountingShell title="Setup" description="Cost centers, branches, currencies, exchange rates and taxes.">
      <Setup />
    </AccountingShell>
  );
}
