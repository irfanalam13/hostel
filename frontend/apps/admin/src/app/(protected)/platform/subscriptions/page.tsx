"use client";

import { PlatformShell } from "@/features/platform/components/primitives";
import { SubscriptionsPanel } from "@/features/platform/components/SubscriptionsPanel";

export default function PlatformSubscriptionsPage() {
  return (
    <PlatformShell title="Subscriptions" description="Assign plans to hostels and review lifecycle history.">
      <SubscriptionsPanel />
    </PlatformShell>
  );
}
