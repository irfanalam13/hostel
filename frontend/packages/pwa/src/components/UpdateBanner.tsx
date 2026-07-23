"use client";

import { usePwa } from "../PwaProvider";

/**
 * "Update available" prompt. Appears when a new service-worker version has been
 * downloaded and is waiting. "Update now" activates it and reloads; "Later"
 * dismisses until the next launch (the waiting worker stays ready).
 */
export function UpdateBanner() {
  const { updateAvailable, applyUpdate } = usePwa();

  if (!updateAvailable) return null;

  return (
    <div
      role="alertdialog"
      aria-label="A new version is available"
      className="anim-slide-up fixed inset-x-0 bottom-0 z-[70] mx-auto mb-[max(1rem,env(safe-area-inset-bottom))] w-[min(92%,30rem)] rounded-2xl border border-[var(--border)] bg-[var(--card-elevated)] p-4 shadow-[var(--shadow-lg)]"
    >
      <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[var(--accent-soft)] text-[var(--accent)]">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
                <path d="M21 2v6h-6" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M3 12a9 9 0 0 1 15-6.7L21 8" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M3 22v-6h6" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M21 12a9 9 0 0 1-15 6.7L3 16" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <div className="min-w-0 flex-1">
              <p className="font-semibold text-[var(--foreground)]">Update available</p>
              <p className="text-sm text-[var(--muted)]">A new version is ready to install.</p>
            </div>
          </div>
          <div className="mt-3 flex justify-end gap-2">
            <button
              onClick={applyUpdate}
              className="rounded-xl bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white transition hover:bg-[var(--accent-hover)]"
            >
              Update now
            </button>
          </div>
    </div>
  );
}
