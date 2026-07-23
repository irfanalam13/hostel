"use client";

import { FinanceShell } from "@/features/finance/components/primitives";
import { RefundManager } from "@/features/finance/components/RefundManager";

export default function RefundsPage() {
  return (
    <FinanceShell title="Refunds" description="Request, approve and process refunds.">
      <RefundManager />
    </FinanceShell>
  );
}
