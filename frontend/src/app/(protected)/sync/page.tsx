"use client";

import { Topbar } from "@/shared/ui/Topbar";
import { SyncCenter } from "@/shared/pwa/components/SyncCenter";

export default function SyncPage() {
  return (
    <div>
      <Topbar title="Offline & Sync" />
      <div className="mx-auto max-w-3xl px-4 py-4 sm:px-6">
        <p className="mb-4 text-sm text-[var(--muted)]">
          Records you create while offline are queued here and synced automatically when you
          reconnect. Duplicates are detected server-side, failed items can be retried, and recent
          sync activity is shown below.
        </p>
        <SyncCenter />
      </div>
    </div>
  );
}
