"use client";

import { usePwa } from "@/shared/providers/PwaProvider";

/**
 * Reusable install button for placing inside the UI (e.g. Settings page).
 * Renders nothing when the app is already installed or installation isn't
 * currently offered by the browser.
 */
export function InstallButton({ className }: { className?: string }) {
  const { isInstallable, isInstalled, installApp } = usePwa();

  if (isInstalled || !isInstallable) return null;

  return (
    <button
      onClick={() => {
        void installApp();
      }}
      className={
        className ??
        "inline-flex items-center gap-2 rounded-xl bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white transition hover:bg-[var(--accent-hover)]"
      }
    >
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
        <path d="M12 3v12m0 0 4-4m-4 4-4-4" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M5 21h14" strokeLinecap="round" />
      </svg>
      Install app
    </button>
  );
}
