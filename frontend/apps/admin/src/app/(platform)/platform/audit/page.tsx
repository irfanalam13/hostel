"use client";

import { PlatformShell } from "@/features/platform/components/primitives";
import { AuditLogViewer } from "@/features/platform/components/AuditLogViewer";

export default function PlatformAuditPage() {
  return (
    <PlatformShell
      title="Audit log"
      description="Searchable, tamper-evident trail of every platform action across every tenant."
    >
      <AuditLogViewer />
    </PlatformShell>
  );
}
