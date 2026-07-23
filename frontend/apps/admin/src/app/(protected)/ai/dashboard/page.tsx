"use client";

import { AiShell } from "@/features/ai/components/primitives";
import { AiDashboard } from "@/features/ai/components/AiDashboard";

export default function AiDashboardPage() {
  return (
    <AiShell title="AI Dashboard" description="AI usage, tokens, latency and model activity.">
      <AiDashboard />
    </AiShell>
  );
}
