"use client";

import { useEffect } from "react";
import { authStore } from "@hostel/auth";
import { getServiceWorkerVersion, isStandalone } from "@hostel/pwa";
import { sendHeartbeat } from "./api";
import { APP_VERSION } from "./types";

const HEARTBEAT_INTERVAL = 45_000;

/**
 * Reports this client's presence to the backend so the system-status dashboard
 * can show online/offline users and installed-PWA counts. Mounted once inside
 * the protected layout (authenticated users only). Pauses while the tab is
 * hidden and fires immediately when it becomes visible again.
 */
export function PresenceHeartbeat() {
  useEffect(() => {
    let stopped = false;
    let inFlight = false;

    const beat = async () => {
      // Overlap guard: never stack a new heartbeat on one that hasn't
      // finished — a slow backend must not accumulate open connections.
      // Also bail if the session marker is gone (logout just cleared it) —
      // the interval is only torn down on unmount, which can lag a step
      // behind the auth state flipping.
      if (stopped || inFlight || document.visibilityState === "hidden" || !authStore.getAccess()) return;
      inFlight = true;
      try {
        const sw = await getServiceWorkerVersion();
        await sendHeartbeat({
          installed: isStandalone(),
          sw_version: sw ?? "",
          app_version: APP_VERSION,
        });
      } catch {
        // Presence is best-effort; the next tick retries.
      } finally {
        inFlight = false;
      }
    };

    void beat();
    const id = window.setInterval(beat, HEARTBEAT_INTERVAL);
    const onVisible = () => {
      if (document.visibilityState === "visible") void beat();
    };
    document.addEventListener("visibilitychange", onVisible);

    return () => {
      stopped = true;
      window.clearInterval(id);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, []);

  return null;
}
