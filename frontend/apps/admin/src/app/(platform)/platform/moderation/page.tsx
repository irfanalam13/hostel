"use client";

import { PlatformShell } from "@/features/platform/components/primitives";
import { ModerationQueue } from "@/features/moderation/components/ModerationQueue";

export default function PlatformModerationPage() {
  return (
    <PlatformShell title="Moderation" description="Flagged discovery reviews awaiting a decision.">
      <ModerationQueue />
    </PlatformShell>
  );
}
