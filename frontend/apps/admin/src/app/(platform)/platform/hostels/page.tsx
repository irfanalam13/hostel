"use client";

import { PlatformShell } from "@/features/platform/components/primitives";
import { HostelsOverviewPanel } from "@/features/platform/components/HostelsOverviewPanel";

export default function PlatformHostelsPage() {
  return (
    <PlatformShell
      title="Hostels overview"
      description="Every workspace's own students, revenue and dues — super-admin only."
    >
      <HostelsOverviewPanel />
    </PlatformShell>
  );
}
