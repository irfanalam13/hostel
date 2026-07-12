"use client";

import { useParams } from "next/navigation";

import { AccountingShell } from "@/features/accounting/components/primitives";
import { JournalDetail } from "@/features/accounting/components/JournalDetail";

export default function JournalDetailPage() {
  const params = useParams();
  const id = Array.isArray(params?.id) ? params.id[0] : (params?.id as string);

  return (
    <AccountingShell title="Journal" description="Lines, totals and workflow actions.">
      <JournalDetail journalId={id} />
    </AccountingShell>
  );
}
