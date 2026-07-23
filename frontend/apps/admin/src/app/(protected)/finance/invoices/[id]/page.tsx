"use client";

import { useParams } from "next/navigation";

import { FinanceShell } from "@/features/finance/components/primitives";
import { InvoiceDetail } from "@/features/finance/components/InvoiceDetail";

export default function InvoiceDetailPage() {
  const params = useParams();
  const id = Array.isArray(params?.id) ? params.id[0] : (params?.id as string);

  return (
    <FinanceShell title="Invoice" description="Line items, adjustments, payments and totals.">
      <InvoiceDetail invoiceId={id} />
    </FinanceShell>
  );
}
