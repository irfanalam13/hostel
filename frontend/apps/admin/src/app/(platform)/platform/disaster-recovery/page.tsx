"use client";

import { PlatformShell } from "@/features/platform/components/primitives";
import { DisasterRecoveryConsole } from "@/features/disaster-recovery/components/DisasterRecoveryConsole";

export default function PlatformDisasterRecoveryPage() {
  return (
    <PlatformShell title="Disaster recovery" description="DR mode, storage usage and restore history — platform-wide.">
      <DisasterRecoveryConsole />
    </PlatformShell>
  );
}
