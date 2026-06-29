"use client";

import { usePwa } from "@/shared/providers/PwaProvider";

/**
 * Persistent connectivity + sync-status indicator. Shows a thin bar at the top
 * when offline, and a "syncing N changes" pill while the outbox drains.
 */
export function OfflineBanner() {
  const { isOnline, pendingSync } = usePwa();
  const show = !isOnline || pendingSync > 0;

  if (!show) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      className="anim-slide-down fixed inset-x-0 top-0 z-[60] flex items-center justify-center gap-2 px-4 py-1.5 text-center text-sm font-medium text-white"
      style={{
        paddingTop: "calc(0.375rem + env(safe-area-inset-top))",
        backgroundColor: isOnline ? "var(--warning)" : "var(--muted)",
      }}
    >
      <span
        className={`h-2 w-2 rounded-full ${isOnline ? "bg-white" : "bg-white/70"} ${
          !isOnline ? "animate-pulse" : ""
        }`}
      />
      {!isOnline
        ? "You're offline — changes are saved and will sync automatically."
        : `Syncing ${pendingSync} pending change${pendingSync === 1 ? "" : "s"}…`}
    </div>
  );
}
