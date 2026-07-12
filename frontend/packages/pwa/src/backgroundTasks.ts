"use client";

/**
 * Background task scheduler.
 * -----------------------------------------------------------------------------
 * Keeps a handful of data sources fresh without the user doing anything:
 *
 *   - refresh-notifications     unread badge / inbox preview
 *   - refresh-announcements     notices feed
 *   - check-updates             pull the latest service worker
 *   - refresh-room-availability bed occupancy summary
 *
 * Two execution layers, picked by capability:
 *
 *   1. Periodic Background Sync API (Chromium, installed PWA, permission
 *      granted) — the service worker runs the tasks even when the app is
 *      CLOSED. Heavily throttled by the browser (hours between runs), so it's
 *      used for "catch up while away" + alerting on new announcements. See the
 *      `periodicsync` handler in public/sw.js.
 *
 *   2. Foreground scheduler (every browser) — while the app is OPEN and the tab
 *      is visible + online, light timers re-run each task on its own cadence and
 *      notify subscribers to refetch. This is the graceful fallback where
 *      Periodic Background Sync is unavailable (Firefox, Safari, uninstalled
 *      Chrome) and the live layer when the app is in use.
 *
 * Components subscribe with `useBackgroundRefresh(id, cb)` and simply refetch in
 * the callback; the scheduler decides when.
 */

import { API_BASE } from "@hostel/api";
import { authStore } from "@hostel/auth/store";
import { hostelStore } from "@hostel/utils";
import { kvSet } from "./db";

export type BackgroundTaskId =
  | "refresh-notifications"
  | "refresh-announcements"
  | "check-updates"
  | "refresh-room-availability";

type TaskDef = {
  id: BackgroundTaskId;
  label: string;
  /** Cadence while the app is open + visible (foreground layer). */
  foregroundIntervalMs: number;
  /** Hint for the browser's Periodic Background Sync (app closed). */
  periodicMinIntervalMs: number;
};

const MIN = 60_000;
const HOUR = 60 * MIN;

export const BACKGROUND_TASKS: readonly TaskDef[] = [
  {
    id: "refresh-notifications",
    label: "Notifications",
    foregroundIntervalMs: 1 * MIN,
    periodicMinIntervalMs: 4 * HOUR,
  },
  {
    id: "refresh-announcements",
    label: "Announcements",
    foregroundIntervalMs: 5 * MIN,
    periodicMinIntervalMs: 12 * HOUR,
  },
  {
    id: "check-updates",
    label: "App updates",
    foregroundIntervalMs: 1 * HOUR,
    periodicMinIntervalMs: 24 * HOUR,
  },
  {
    id: "refresh-room-availability",
    label: "Room availability",
    foregroundIntervalMs: 2 * MIN,
    periodicMinIntervalMs: 12 * HOUR,
  },
];

/* ------------------------------ pub / sub ------------------------------- */
const subscribers = new Map<BackgroundTaskId, Set<() => void>>();

/** Subscribe to a task's ticks. Returns an unsubscribe fn. */
export function onBackgroundTask(id: BackgroundTaskId, cb: () => void): () => void {
  let set = subscribers.get(id);
  if (!set) {
    set = new Set();
    subscribers.set(id, set);
  }
  set.add(cb);
  return () => set!.delete(cb);
}

/**
 * Fire a task's subscribers. Called by the foreground scheduler and by
 * PwaProvider when the service worker reports a background refresh (BG_REFRESH),
 * so an open tab updates immediately after the SW refreshes data while hidden.
 */
export function dispatchBackgroundTask(id: BackgroundTaskId): void {
  subscribers.get(id)?.forEach((cb) => {
    try {
      cb();
    } catch {
      /* a misbehaving subscriber must not break the others */
    }
  });
}

/* --------------------------- foreground layer --------------------------- */
let started = false;
const timers: number[] = [];
const lastRun = new Map<BackgroundTaskId, number>();

function canRun(): boolean {
  return (
    typeof document !== "undefined" &&
    document.visibilityState === "visible" &&
    (typeof navigator === "undefined" || navigator.onLine !== false)
  );
}

async function runTask(task: TaskDef): Promise<void> {
  lastRun.set(task.id, Date.now());

  // The update check is owned by the scheduler itself (no UI subscriber needed):
  // pull the newest service worker; register.ts surfaces the UpdateBanner if one
  // is waiting.
  if (task.id === "check-updates") {
    try {
      const reg = await navigator.serviceWorker?.ready;
      await reg?.update();
    } catch {
      /* best effort */
    }
  }

  dispatchBackgroundTask(task.id);
}

/** Run every task whose foreground interval has elapsed (catch-up). */
function runDue(): void {
  if (!canRun()) return;
  const now = Date.now();
  for (const task of BACKGROUND_TASKS) {
    if (now - (lastRun.get(task.id) ?? 0) >= task.foregroundIntervalMs) {
      void runTask(task);
    }
  }
}

/**
 * Start the background-task layers. Idempotent. Returns a cleanup fn that tears
 * down the foreground timers + listeners (Periodic Background Sync registrations
 * persist in the browser and are intentionally left in place).
 */
export function initBackgroundTasks(): () => void {
  if (started || typeof window === "undefined") return () => {};
  started = true;

  // Hand the service worker what it needs to make authenticated background
  // fetches (the SW can't read localStorage / app modules).
  void persistConfig();

  // Best-effort true-background registration; silently a no-op where unsupported.
  void registerPeriodicSync();

  // One timer per task; each no-ops while hidden/offline and catches up on
  // visibility/reconnect via runDue().
  for (const task of BACKGROUND_TASKS) {
    const id = window.setInterval(() => {
      if (canRun()) void runTask(task);
    }, task.foregroundIntervalMs);
    timers.push(id);
  }

  const onVisible = () => {
    if (document.visibilityState === "visible") runDue();
  };
  const onOnline = () => runDue();

  document.addEventListener("visibilitychange", onVisible);
  window.addEventListener("online", onOnline);

  // Prime everything once on startup.
  runDue();

  return () => {
    started = false;
    timers.splice(0).forEach((id) => window.clearInterval(id));
    document.removeEventListener("visibilitychange", onVisible);
    window.removeEventListener("online", onOnline);
  };
}

/* ----------------------- periodic background sync ----------------------- */
type PeriodicSyncManager = {
  register: (tag: string, options?: { minInterval: number }) => Promise<void>;
  getTags: () => Promise<string[]>;
};

function getPeriodicSync(reg: ServiceWorkerRegistration): PeriodicSyncManager | null {
  return (reg as unknown as { periodicSync?: PeriodicSyncManager }).periodicSync ?? null;
}

async function persistConfig(): Promise<void> {
  try {
    await kvSet("bg-config", {
      apiBase: API_BASE,
      hostelCode: authStore.getHostelCode() || hostelStore.getCode() || null,
      updatedAt: Date.now(),
    });
  } catch {
    /* IndexedDB unavailable — foreground layer still works */
  }
}

/** Re-persist config so the SW always has the current hostel/session context. */
export function syncBackgroundConfig(): void {
  void persistConfig();
}

async function registerPeriodicSync(): Promise<void> {
  if (typeof navigator === "undefined" || !("serviceWorker" in navigator)) return;
  let reg: ServiceWorkerRegistration;
  try {
    reg = await navigator.serviceWorker.ready;
  } catch {
    return;
  }
  const periodicSync = getPeriodicSync(reg);
  if (!periodicSync) return; // unsupported → foreground only

  // The permission is only ever granted to installed PWAs with enough
  // engagement; if it isn't granted, registering throws — so gate on it.
  try {
    const status = await navigator.permissions.query({
      name: "periodic-background-sync" as PermissionName,
    });
    if (status.state !== "granted") return;
  } catch {
    // Some engines don't know this permission name; fall through and let the
    // register() call below succeed-or-throw on its own.
  }

  for (const task of BACKGROUND_TASKS) {
    try {
      await periodicSync.register(task.id, { minInterval: task.periodicMinIntervalMs });
    } catch {
      /* best effort per tag */
    }
  }
}

/* ------------------------------ status (UI) ----------------------------- */
export type BackgroundSyncStatus = {
  /** Periodic Background Sync exists in this browser. */
  supported: boolean;
  /** Permission state for periodic-background-sync, if queryable. */
  permission: PermissionState | "unknown";
  /** Tags the browser has actually registered for true-background runs. */
  registeredTags: string[];
};

/** Snapshot for the settings UI: is true-background active, or foreground-only? */
export async function getBackgroundSyncStatus(): Promise<BackgroundSyncStatus> {
  const fallback: BackgroundSyncStatus = {
    supported: false,
    permission: "unknown",
    registeredTags: [],
  };
  if (typeof navigator === "undefined" || !("serviceWorker" in navigator)) return fallback;

  let reg: ServiceWorkerRegistration;
  try {
    reg = await navigator.serviceWorker.ready;
  } catch {
    return fallback;
  }
  const periodicSync = getPeriodicSync(reg);
  if (!periodicSync) return fallback;

  let permission: PermissionState | "unknown" = "unknown";
  try {
    const status = await navigator.permissions.query({
      name: "periodic-background-sync" as PermissionName,
    });
    permission = status.state;
  } catch {
    /* not queryable */
  }

  let registeredTags: string[] = [];
  try {
    registeredTags = await periodicSync.getTags();
  } catch {
    /* getTags unsupported */
  }

  return { supported: true, permission, registeredTags };
}
