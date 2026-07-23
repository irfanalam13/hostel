"use client";

import { FinanceShell } from "@/features/finance/components/primitives";
import { ExpenseManager } from "@/features/finance/components/ExpenseManager";

export default function ExpensesPage() {
  return (
    <FinanceShell title="Expenses" description="Record, approve and settle operational expenses.">
      <ExpenseManager />
    </FinanceShell>
  );
}
