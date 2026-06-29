"use client";

import { useEffect } from "react";
import { getServiceWorkerVersion, isStandalone } from "@/shared/pwa/register";
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

    const beat = async () => {
      if (stopped || document.visibilityState === "hidden") return;
      const sw = await getServiceWorkerVersion();
      void sendHeartbeat({
        installed: isStandalone(),
        sw_version: sw ?? "",
        app_version: APP_VERSION,
      });
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
