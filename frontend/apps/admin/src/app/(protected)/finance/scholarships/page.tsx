"use client";

import { FinanceShell } from "@/features/finance/components/primitives";
import { ScholarshipManager } from "@/features/finance/components/ScholarshipManager";

export default function ScholarshipsPage() {
  return (
    <FinanceShell title="Scholarships" description="Scholarship programs and resident awards.">
      <ScholarshipManager />
    </FinanceShell>
  );
}
