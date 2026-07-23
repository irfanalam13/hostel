"use client";

import { PlatformShell } from "@/features/platform/components/primitives";
import { OverridesPanel } from "@/features/platform/components/OverridesPanel";

export default function PlatformOverridesPage() {
  return (
    <PlatformShell
      title="Overrides"
      description="Grant or revoke features and adjust limits for individual hostels."
    >
      <OverridesPanel />
    </PlatformShell>
  );
}
