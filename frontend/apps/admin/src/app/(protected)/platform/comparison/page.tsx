"use client";

import { PlatformShell } from "@/features/platform/components/primitives";
import { ComparisonMatrix } from "@/features/platform/components/ComparisonMatrix";

export default function PlatformComparisonPage() {
  return (
    <PlatformShell title="Plan comparison" description="Feature and limit matrix across all plans.">
      <ComparisonMatrix />
    </PlatformShell>
  );
}
