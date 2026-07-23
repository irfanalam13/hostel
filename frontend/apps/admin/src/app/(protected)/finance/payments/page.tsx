"use client";

import { FinanceShell } from "@/features/finance/components/primitives";
import { PaymentList } from "@/features/finance/components/PaymentList";

export default function PaymentsPage() {
  return (
    <FinanceShell title="Payments" description="Collect, verify and reconcile payments.">
      <PaymentList />
    </FinanceShell>
  );
}
