"use client";

import { AccountingShell } from "@/features/accounting/components/primitives";
import { FixedAssets } from "@/features/accounting/components/FixedAssets";

export default function AssetsPage() {
  return (
    <AccountingShell title="Fixed Assets" description="Asset register, depreciation and disposal.">
      <FixedAssets />
    </AccountingShell>
  );
}
