"use client";

import { FinanceShell } from "@/features/finance/components/primitives";
import { InvoiceList } from "@/features/finance/components/InvoiceList";

export default function InvoicesPage() {
  return (
    <FinanceShell title="Invoices" description="Raise, issue and track resident invoices.">
      <InvoiceList />
    </FinanceShell>
  );
}
