"use client";

import { useEffect, useState } from "react";
import { usePwa } from "../PwaProvider";
import { InstallButton } from "./InstallButton";
import {
  getSubscription,
  permissionState,
  pushConfigured,
  subscribeToPush,
  unsubscribeFromPush,
} from "../push";
import { useToast } from "@hostel/ui";
import { getBackgroundSyncStatus, type BackgroundSyncStatus } from "../backgroundTasks";

/**
 * User-facing PWA controls: install status, push-notification toggle, and the
 * offline sync queue. Drop into Settings. Each control hides itself when the
 * underlying capability isn't available in the current browser.
 */
export function PwaSettingsCard() {
  const toast = useToast();
  const { isInstalled, isInstallable, pendingSync, isOnline } = usePwa();
  const [pushOn, setPushOn] = useState(false);
  const [busy, setBusy] = useState(false);
  const [bgStatus, setBgStatus] = useState<BackgroundSyncStatus | null>(null);
  const configured = pushConfigured();
  const denied = permissionState() === "denied";

  // True background = Periodic Background Sync registered; otherwise the
  // foreground scheduler keeps things fresh only while the app is open.
  const trueBackground = !!bgStatus?.supported && bgStatus.registeredTags.length > 0;

  useEffect(() => {
    void getSubscription().then((s) => setPushOn(!!s));
    void getBackgroundSyncStatus().then(setBgStatus);
  }, []);

  const togglePush = async () => {
    setBusy(true);
    try {
      if (pushOn) {
        await unsubscribeFromPush();
        setPushOn(false);
        toast.info("Notifications turned off.");
      } else {
        const sub = await subscribeToPush();
        if (sub) {
          setPushOn(true);
          toast.success("Notifications enabled.");
        } else if (permissionState() === "denied") {
          toast.error("Notifications are blocked in your browser settings.");
        }
      }
    } catch {
      toast.error("Couldn't update notification settings.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="rounded-2xl border border-[var(--border)] bg-[var(--card)] p-4 space-y-4 text-sm">
      <h2 className="text-base font-semibold text-[var(--foreground)]">App &amp; notifications</h2>

      {/* Install */}
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="font-medium text-[var(--foreground)]">Install app</p>
          <p className="text-[var(--muted)]">
            {isInstalled
              ? "Installed — running as an app."
              : isInstallable
                ? "Add to your home screen or desktop."
                : "Use your browser menu to install."}
          </p>
        </div>
        {isInstalled ? (
          <span className="rounded-full bg-[var(--success)]/10 px-3 py-1 text-[var(--success)]">Installed</span>
        ) : (
          <InstallButton />
        )}
      </div>

      {/* Push notifications */}
      {configured && (
        <div className="flex items-center justify-between gap-4 border-t border-[var(--border)] pt-4">
          <div>
            <p className="font-medium text-[var(--foreground)]">Push notifications</p>
            <p className="text-[var(--muted)]">
              {denied
                ? "Blocked in browser settings."
                : "Announcements, payment reminders and admission updates."}
            </p>
          </div>
          <button
            onClick={togglePush}
            disabled={busy || denied}
            role="switch"
            aria-checked={pushOn}
            className={`relative h-6 w-11 shrink-0 rounded-full transition disabled:opacity-50 ${
              pushOn ? "bg-[var(--accent)]" : "bg-[var(--border-hover)]"
            }`}
          >
            <span
              className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-all ${
                pushOn ? "left-[22px]" : "left-0.5"
              }`}
            />
          </button>
        </div>
      )}

      {/* Background updates */}
      <div className="flex items-center justify-between gap-4 border-t border-[var(--border)] pt-4">
        <div>
          <p className="font-medium text-[var(--foreground)]">Background updates</p>
          <p className="text-[var(--muted)]">
            {trueBackground
              ? "Notifications, announcements and room availability refresh automatically — even when the app is closed."
              : "Notifications, announcements and room availability refresh while the app is open."}
          </p>
        </div>
        <span
          className={`shrink-0 rounded-full px-3 py-1 ${
            trueBackground
              ? "bg-[var(--success)]/10 text-[var(--success)]"
              : "bg-[var(--muted)]/10 text-[var(--muted)]"
          }`}
        >
          {trueBackground ? "Background" : "While open"}
        </span>
      </div>

      {/* Sync status */}
      <div className="flex items-center justify-between gap-4 border-t border-[var(--border)] pt-4">
        <div>
          <p className="font-medium text-[var(--foreground)]">Offline sync</p>
          <p className="text-[var(--muted)]">
            {pendingSync > 0
              ? `${pendingSync} change${pendingSync === 1 ? "" : "s"} waiting to sync.`
              : "All changes synced."}
          </p>
        </div>
        <span
          className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 ${
            isOnline ? "bg-[var(--success)]/10 text-[var(--success)]" : "bg-[var(--muted)]/10 text-[var(--muted)]"
          }`}
        >
          <span className={`h-2 w-2 rounded-full ${isOnline ? "bg-[var(--success)]" : "bg-[var(--muted)]"}`} />
          {isOnline ? "Online" : "Offline"}
        </span>
      </div>
    </div>
  );
}
