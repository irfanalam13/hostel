"use client";

import { PlatformShell } from "@/features/platform/components/primitives";
import { AnalyticsDashboard } from "@/features/platform/components/AnalyticsDashboard";

export default function PlatformAnalyticsPage() {
  return (
    <PlatformShell title="Analytics" description="Revenue, plan distribution and feature adoption.">
      <AnalyticsDashboard />
    </PlatformShell>
  );
}
