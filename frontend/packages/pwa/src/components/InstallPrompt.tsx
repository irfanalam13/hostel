"use client";

import { useEffect, useState } from "react";
import { usePwa } from "../PwaProvider";

const SNOOZE_KEY = "pwa-install-snoozed-until";
const SNOOZE_DAYS = 7;

function isIos(): boolean {
  if (typeof navigator === "undefined") return false;
  return /iphone|ipad|ipod/i.test(navigator.userAgent) && !/crios|fxios/i.test(navigator.userAgent);
}

/**
 * Install banner. On Chromium it uses the captured beforeinstallprompt; on iOS
 * Safari (which has no install event) it shows "Add to Home Screen" guidance.
 * Dismissing snoozes the banner for a week so it isn't nagging.
 */
export function InstallPrompt() {
  const { isInstallable, isInstalled, installApp } = usePwa();
  const [snoozed, setSnoozed] = useState(true); // default hidden until checked
  const [ios, setIos] = useState(false);

  useEffect(() => {
    setIos(isIos());
    const until = Number(localStorage.getItem(SNOOZE_KEY) || 0);
    setSnoozed(Date.now() < until);
  }, []);

  const snooze = () => {
    localStorage.setItem(SNOOZE_KEY, String(Date.now() + SNOOZE_DAYS * 86_400_000));
    setSnoozed(true);
  };

  // Show when: not installed, not snoozed, and either we have a prompt (Chromium)
  // or we're on iOS Safari (manual instructions).
  const canShow = !isInstalled && !snoozed && (isInstallable || ios);

  if (!canShow) return null;

  return (
    <div
      role="dialog"
      aria-label="Install app"
      className="anim-slide-up fixed inset-x-0 bottom-0 z-[65] mx-auto mb-[max(1rem,env(safe-area-inset-bottom))] w-[min(92%,30rem)] rounded-2xl border border-[var(--border)] bg-[var(--card-elevated)] p-4 shadow-[var(--shadow-lg)]"
    >
      <div className="flex items-start gap-3">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/icons/icon-192.png" alt="" width={44} height={44} className="rounded-xl" />
            <div className="min-w-0 flex-1">
              <p className="font-semibold text-[var(--foreground)]">Install MY Hostel</p>
              {ios && !isInstallable ? (
                <p className="text-sm text-[var(--muted)]">
                  Tap the Share icon, then <strong>Add to Home Screen</strong>.
                </p>
              ) : (
                <p className="text-sm text-[var(--muted)]">
                  Add to your home screen for a faster, full-screen, offline-ready experience.
                </p>
              )}
            </div>
            <button
              onClick={snooze}
              aria-label="Dismiss"
              className="rounded-lg p-1 text-[var(--muted)] transition hover:bg-[var(--background-secondary)]"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
                <path d="M18 6 6 18M6 6l12 12" strokeLinecap="round" />
              </svg>
            </button>
          </div>
          {(isInstallable || !ios) && (
            <div className="mt-3 flex justify-end gap-2">
              <button
                onClick={snooze}
                className="rounded-xl border border-[var(--border)] px-4 py-2 text-sm font-medium transition hover:bg-[var(--background-secondary)]"
              >
                Not now
              </button>
              <button
                onClick={() => {
                  void installApp();
                }}
                disabled={!isInstallable}
                className="rounded-xl bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white transition hover:bg-[var(--accent-hover)] disabled:opacity-50"
              >
                Install
              </button>
            </div>
          )}
    </div>
  );
}
