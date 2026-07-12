"use client";

import { AccountingShell } from "@/features/accounting/components/primitives";
import { JournalList } from "@/features/accounting/components/JournalList";

export default function JournalsPage() {
  return (
    <AccountingShell title="Journals" description="Record, approve and post journal entries.">
      <JournalList />
    </AccountingShell>
  );
}
