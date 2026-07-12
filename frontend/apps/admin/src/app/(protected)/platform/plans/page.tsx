"use client";

import { PlatformShell } from "@/features/platform/components/primitives";
import { PlanList } from "@/features/platform/components/PlanList";

export default function PlatformPlansPage() {
  return (
    <PlatformShell title="Plans" description="Create, price and configure subscription plans.">
      <PlanList />
    </PlatformShell>
  );
}
