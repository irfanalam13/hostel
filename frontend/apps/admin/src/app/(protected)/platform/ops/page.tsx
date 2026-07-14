"use client";

import { PlatformShell } from "@/features/platform/components/primitives";
import { OpsGovConsole } from "@/features/opsgov/components/OpsGovConsole";

export default function PlatformOpsPage() {
  return (
    <PlatformShell
      title="Operations governance"
      description="System announcements, scheduled maintenance, incident tracking and feature flags."
    >
      <OpsGovConsole />
    </PlatformShell>
  );
}
