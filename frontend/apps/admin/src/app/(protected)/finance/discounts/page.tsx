"use client";

import { FinanceShell } from "@/features/finance/components/primitives";
import { DiscountManager } from "@/features/finance/components/DiscountManager";

export default function DiscountsPage() {
  return (
    <FinanceShell title="Discounts" description="Manage discount schemes and eligibility.">
      <DiscountManager />
    </FinanceShell>
  );
}
