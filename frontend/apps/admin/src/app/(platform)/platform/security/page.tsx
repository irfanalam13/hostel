"use client";

import { PlatformShell } from "@/features/platform/components/primitives";
import { SecurityConsole } from "@/features/security/components/SecurityConsole";

export default function PlatformSecurityPage() {
  return (
    <PlatformShell
      title="Security"
      description="Threat events, IP rules, reputation and the emergency kill switch."
    >
      <SecurityConsole />
    </PlatformShell>
  );
}
