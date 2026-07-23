"use client";

import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { useToast } from "@hostel/ui";
import { applyUpdate as applySwUpdate, isStandalone, registerServiceWorker } from "./register";
import { initOutboxAutoFlush, pendingCount } from "./outbox";
import { autoCleanupIfNeeded } from "./storage";
import { flush as flushAnalytics, initAnalytics, track } from "./analytics";
import { PwaShell } from "./components/PwaShell";
import { installTrustedTypes } from "@hostel/config";
import {
  dispatchBackgroundTask,
  initBackgroundTasks,
  type BackgroundTaskId,
} from "./backgroundTasks";

// Install the Trusted Types default policy as soon as the client bundle
// evaluates — before any component effect can reach a DOM injection sink.
installTrustedTypes();

type BeforeInstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
};

type PwaContextType = {
  /** Live network status. */
  isOnline: boolean;
  /** A beforeinstallprompt was captured and the app isn't installed yet. */
  isInstallable: boolean;
  /** Running as an installed app (standalone / WCO). */
  isInstalled: boolean;
  /** Trigger the native install prompt. */
  installApp: () => Promise<void>;
  /** A new service-worker version is waiting to activate. */
  updateAvailable: boolean;
  /** Activate the waiting worker and reload. */
  applyUpdate: () => void;
  /** Number of mutations queued in the offline outbox. */
  pendingSync: number;
  /** Re-read the pending outbox count (e.g. after queuing a request). */
  refreshPending: () => void;
};

const PwaContext = createContext<PwaContextType | undefined>(undefined);

export function PwaProvider({ children }: { children: React.ReactNode }) {
  const toast = useToast();
  const [isOnline, setIsOnline] = useState(true);
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [isInstallable, setIsInstallable] = useState(false);
  const [isInstalled, setIsInstalled] = useState(false);
  const [updateAvailable, setUpdateAvailable] = useState(false);
  const [pendingSync, setPendingSync] = useState(0);
  const offlineSince = useRef<number | null>(null);

  const refreshPending = useCallback(() => {
    void pendingCount().then(setPendingSync);
  }, []);

  useEffect(() => {
    setIsInstalled(isStandalone());

    // 0. Telemetry flush loop + global error capture.
    const stopAnalytics = initAnalytics();

    // 1. Service worker registration + update detection.
    registerServiceWorker({
      onUpdateAvailable: () => {
        setUpdateAvailable(true);
        track("UPDATE_AVAILABLE");
      },
      onMessage: (data) => {
        const msg = data as {
          type?: string;
          count?: number;
          failed?: number;
          hits?: number;
          misses?: number;
          url?: string;
          tag?: string;
          task?: BackgroundTaskId;
        };
        if (msg?.type === "OUTBOX_SYNCED") {
          if (msg.count) {
            toast.success(`Synced ${msg.count} pending change${msg.count === 1 ? "" : "s"}.`);
            track("SYNC_SUCCESS", { value: msg.count });
          }
          if (msg.failed) track("SYNC_FAILURE", { value: msg.failed });
          refreshPending();
          // Let the Sync Center refresh its queue + history live.
          window.dispatchEvent(new Event("sync-log-updated"));
        } else if (msg?.type === "SYNC_LOG_UPDATED") {
          // Outbox state changed (retry/backoff/dead-letter) without a successful
          // sync — refresh counters + the Sync Center without a success toast.
          refreshPending();
          window.dispatchEvent(new Event("sync-log-updated"));
        } else if (msg?.type === "CACHE_STATS") {
          if (msg.hits) track("CACHE_HIT", { value: msg.hits });
          if (msg.misses) track("CACHE_MISS", { value: msg.misses });
        } else if (msg?.type === "PUSH_RECEIVED") {
          track("PUSH_RECEIVED", { meta: { tag: msg.tag } });
        } else if (msg?.type === "PUSH_OPEN") {
          track("PUSH_OPEN", { meta: { url: msg.url } });
        } else if (msg?.type === "BG_REFRESH" && msg.task) {
          // The SW refreshed data in the background — tell any live subscribers
          // (e.g. the notification bell) to re-pull so the UI matches.
          dispatchBackgroundTask(msg.task);
        }
      },
    });

    // 2. Offline write-queue auto-flush on reconnect.
    const stopAutoFlush = initOutboxAutoFlush();
    refreshPending();

    // 2a. Background tasks: keep notifications/notices/beds fresh and pull SW
    // updates — via Periodic Background Sync where supported, foreground timers
    // everywhere else.
    const stopBackgroundTasks = initBackgroundTasks();

    // 2b. Quota monitoring + automatic cleanup on launch. If storage is
    // critically full we shed regenerable download caches automatically; if it's
    // just getting full we nudge the user toward Settings → Storage.
    void autoCleanupIfNeeded().then(({ ran, freedBuckets, before }) => {
      if (ran) {
        toast.warning(
          `Storage was almost full — freed ${freedBuckets} cache bucket${freedBuckets === 1 ? "" : "s"}.`,
        );
      } else if (before.supported && before.level === "warn") {
        toast.info("Device storage is getting full. Clear cached downloads in Settings → Storage.");
      }
    });

    // 3. Online/offline tracking.
    const handleOnline = () => {
      setIsOnline(true);
      toast.success("Back online. Syncing…");
      refreshPending();
      if (offlineSince.current) {
        track("OFFLINE_SESSION", { value: Math.round((Date.now() - offlineSince.current) / 1000) });
        offlineSince.current = null;
      }
    };
    const handleOffline = () => {
      setIsOnline(false);
      offlineSince.current = Date.now();
      toast.info("You're offline. Changes will sync when you reconnect.");
    };
    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);
    setIsOnline(navigator.onLine);

    // 4. Install prompt capture.
    const handleBeforeInstallPrompt = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e as BeforeInstallPromptEvent);
      setIsInstallable(true);
      track("INSTALL_PROMPT");
    };
    window.addEventListener("beforeinstallprompt", handleBeforeInstallPrompt);

    // 5. Installed analytics + state.
    const handleAppInstalled = () => {
      setIsInstallable(false);
      setDeferredPrompt(null);
      setIsInstalled(true);
      track("INSTALLED");
      toast.success("App installed.");
    };
    window.addEventListener("appinstalled", handleAppInstalled);

    // 6. React to display-mode changes (installed/uninstalled at runtime).
    const mq = window.matchMedia("(display-mode: standalone)");
    const onDisplayChange = () => setIsInstalled(isStandalone());
    mq.addEventListener?.("change", onDisplayChange);

    return () => {
      stopAutoFlush();
      stopBackgroundTasks();
      stopAnalytics();
      void flushAnalytics();
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
      window.removeEventListener("beforeinstallprompt", handleBeforeInstallPrompt);
      window.removeEventListener("appinstalled", handleAppInstalled);
      mq.removeEventListener?.("change", onDisplayChange);
    };
  }, [toast, refreshPending]);

  const installApp = useCallback(async () => {
    if (!deferredPrompt) return;
    await deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    track(outcome === "accepted" ? "INSTALL_ACCEPTED" : "INSTALL_DISMISSED");
    if (outcome === "accepted") {
      setIsInstallable(false);
      setDeferredPrompt(null);
    }
  }, [deferredPrompt]);

  const applyUpdate = useCallback(() => {
    track("UPDATE_APPLIED");
    // Flush before the reload that applying the update triggers.
    void flushAnalytics().finally(() => applySwUpdate());
  }, []);

  return (
    <PwaContext.Provider
      value={{
        isOnline,
        isInstallable,
        isInstalled,
        installApp,
        updateAvailable,
        applyUpdate,
        pendingSync,
        refreshPending,
      }}
    >
      {children}
      <PwaShell />
    </PwaContext.Provider>
  );
}

export function usePwa() {
  const context = useContext(PwaContext);
  if (!context) {
    throw new Error("usePwa must be used within a PwaProvider");
  }
  return context;
}
