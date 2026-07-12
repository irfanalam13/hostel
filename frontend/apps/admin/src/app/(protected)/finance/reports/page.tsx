"use client";

import { FinanceShell } from "@/features/finance/components/primitives";
import { FinanceReports } from "@/features/finance/components/FinanceReports";

export default function ReportsPage() {
  return (
    <FinanceShell title="Reports" description="Collections, profit &amp; loss, dues and exports.">
      <FinanceReports />
    </FinanceShell>
  );
}
