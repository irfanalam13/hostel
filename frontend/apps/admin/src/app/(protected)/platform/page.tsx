"use client";

import { PlatformShell } from "@/features/platform/components/primitives";
import { PlatformHome } from "@/features/platform/components/PlatformHome";

export default function PlatformOverviewPage() {
  return (
    <PlatformShell
      title="Subscription platform"
      description="Manage plans, features, limits and per-hostel overrides."
    >
      <PlatformHome />
    </PlatformShell>
  );
}
