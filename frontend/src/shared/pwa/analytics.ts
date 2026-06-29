/**
 * PWA telemetry client.
 *
 * Buffers events in memory and flushes them in batches to the backend
 * (/api/analytics/collect/). Auto-captured signals (install, update, offline,
 * push, sync, cache, errors) are wired in PwaProvider; feature usage is tracked
 * on route changes. Everything is best-effort and wrapped so telemetry can never
 * break the app. Device type / browser are derived server-side from the
 * User-Agent, so we don't send them here.
 */
import { api } from "@/shared/api/apiClient";
import { authStore } from "@/shared/auth/auth.store";
import { getServiceWorkerVersion } from "./register";

export type AnalyticsEventType =
  | "INSTALL_PROMPT"
  | "INSTALL_ACCEPTED"
  | "INSTALL_DISMISSED"
  | "INSTALLED"
  | "UPDATE_AVAILABLE"
  | "UPDATE_APPLIED"
  | "OFFLINE_SESSION"
  | "FEATURE_USED"
  | "PUSH_RECEIVED"
  | "PUSH_OPEN"
  | "CACHE_HIT"
  | "CACHE_MISS"
  | "SYNC_SUCCESS"
  | "SYNC_FAILURE"
  | "ERROR";

type QueuedEvent = {
  event_type: AnalyticsEventType;
  name?: string;
  value?: number;
  occurred_at: string;
  meta?: Record<string, unknown>;
};

const APP_VERSION = process.env.NEXT_PUBLIC_APP_VERSION?.trim() || "1.0.0";
const FLUSH_INTERVAL = 15_000;
const MAX_QUEUE = 200; // hard cap so a long offline spell can't grow unbounded

let queue: QueuedEvent[] = [];
let swVersion = "";
let flushing = false;
let started = false;

/** Record a telemetry event. Safe to call anywhere; never throws. */
export function track(
  event_type: AnalyticsEventType,
  opts: { name?: string; value?: number; meta?: Record<string, unknown> } = {},
): void {
  try {
    queue.push({
      event_type,
      name: opts.name,
      value: opts.value,
      meta: opts.meta,
      occurred_at: new Date().toISOString(),
    });
    if (queue.length > MAX_QUEUE) queue = queue.slice(-MAX_QUEUE);
  } catch {
    /* ignore */
  }
}

/** Convenience for FEATURE_USED. */
export function trackFeature(name: string): void {
  if (name) track("FEATURE_USED", { name });
}

export async function flush(): Promise<void> {
  if (flushing || queue.length === 0) return;
  // Telemetry is owner-facing and the endpoint requires auth. Skip flushing for
  // anonymous visitors (e.g. on the public landing page) so we don't fire a
  // doomed authenticated request that would 401 and disturb the auth state.
  if (!authStore.getAccess()) return;
  flushing = true;
  const batch = queue;
  queue = [];
  try {
    await api.post("/analytics/collect/", {
      events: batch,
      app_version: APP_VERSION,
      sw_version: swVersion,
    });
  } catch {
    // Re-queue (bounded) so a transient failure doesn't lose events.
    queue = [...batch, ...queue].slice(-MAX_QUEUE);
  } finally {
    flushing = false;
  }
}

/**
 * Start the flush loop + global error capture. Idempotent. Returns a cleanup
 * function. Called once from PwaProvider.
 */
export function initAnalytics(): () => void {
  if (started || typeof window === "undefined") return () => {};
  started = true;

  void getServiceWorkerVersion().then((v) => {
    swVersion = v ?? "";
  });

  const interval = window.setInterval(() => void flush(), FLUSH_INTERVAL);

  // Flush opportunistically when the tab is hidden (page may be closing).
  const onHidden = () => {
    if (document.visibilityState === "hidden") void flush();
  };
  document.addEventListener("visibilitychange", onHidden);

  // Error frequency.
  let lastError = 0;
  const onError = (ev: ErrorEvent) => {
    const now = Date.now();
    if (now - lastError < 1000) return; // throttle bursts
    lastError = now;
    track("ERROR", {
      name: (ev.message || "error").slice(0, 200),
      meta: { source: ev.filename, line: ev.lineno },
    });
  };
  const onRejection = (ev: PromiseRejectionEvent) => {
    track("ERROR", { name: String(ev.reason).slice(0, 200), meta: { kind: "unhandledrejection" } });
  };
  window.addEventListener("error", onError);
  window.addEventListener("unhandledrejection", onRejection);

  return () => {
    started = false;
    window.clearInterval(interval);
    document.removeEventListener("visibilitychange", onHidden);
    window.removeEventListener("error", onError);
    window.removeEventListener("unhandledrejection", onRejection);
  };
}
