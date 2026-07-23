/**
 * Storage management for the PWA.
 *
 * Surfaces and controls everything the app persists on-device:
 *   - Device storage estimation        navigator.storage.estimate()
 *   - Cache Storage usage (per bucket)  the SW's hms-* caches
 *   - IndexedDB usage                   the hostel-pwa DB (outbox + keyval)
 *   - Clear cache / clear downloads     delete cache buckets
 *   - Export offline data               download outbox + keyval as JSON
 *   - Quota monitoring + warnings       thresholds + persisted-storage request
 *   - Automatic cleanup                 shed regenerable caches when critical
 *
 * Everything degrades gracefully when an API is unavailable (older Safari, etc.).
 */
import { kvEntries, outboxAll } from "./db";

const CACHE_PREFIX = "hms-";
// Buckets that hold regenerable "downloaded" content (vs. the app shell).
const DOWNLOAD_BUCKET_HINTS = ["images", "pages"];

export const STORAGE_WARN_AT = 0.8; // 80%
export const STORAGE_CRITICAL_AT = 0.95; // 95%

export type StorageLevel = "ok" | "warn" | "critical";

export type StorageEstimateResult = {
  supported: boolean;
  usage: number;
  quota: number;
  percent: number; // 0..1 (usage/quota)
  persisted: boolean;
  level: StorageLevel;
};

export type CacheBucket = { name: string; entries: number; bytes: number; isDownload: boolean };
export type CacheUsage = { total: number; buckets: CacheBucket[] };
export type IndexedDbUsage = { bytes: number; outbox: number; keyval: number; outboxItems: number };

/* ------------------------------- helpers -------------------------------- */
export function formatBytes(bytes: number): string {
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / Math.pow(1024, i)).toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

export function storageLevel(percent: number): StorageLevel {
  if (percent >= STORAGE_CRITICAL_AT) return "critical";
  if (percent >= STORAGE_WARN_AT) return "warn";
  return "ok";
}

function byteLength(s: string): number {
  return new Blob([s]).size;
}

async function responseSize(res: Response): Promise<number> {
  const len = res.headers.get("content-length");
  if (len) {
    const n = parseInt(len, 10);
    if (!Number.isNaN(n)) return n;
  }
  try {
    return (await res.clone().blob()).size;
  } catch {
    return 0;
  }
}

/* --------------------------- device estimation -------------------------- */
export async function estimateStorage(): Promise<StorageEstimateResult> {
  if (typeof navigator === "undefined" || !navigator.storage?.estimate) {
    return { supported: false, usage: 0, quota: 0, percent: 0, persisted: false, level: "ok" };
  }
  const est = await navigator.storage.estimate();
  const usage = est.usage ?? 0;
  const quota = est.quota ?? 0;
  const percent = quota > 0 ? usage / quota : 0;
  let persisted = false;
  try {
    persisted = navigator.storage.persisted ? await navigator.storage.persisted() : false;
  } catch {
    /* ignore */
  }
  return { supported: true, usage, quota, percent, persisted, level: storageLevel(percent) };
}

/** Ask the browser to make our storage persistent (won't be auto-evicted). */
export async function requestPersistentStorage(): Promise<boolean> {
  if (typeof navigator === "undefined" || !navigator.storage?.persist) return false;
  try {
    if (navigator.storage.persisted && (await navigator.storage.persisted())) return true;
    return await navigator.storage.persist();
  } catch {
    return false;
  }
}

/* ----------------------------- cache usage ------------------------------ */
export async function cacheUsage(): Promise<CacheUsage> {
  if (typeof caches === "undefined") return { total: 0, buckets: [] };
  const names = (await caches.keys()).filter((n) => n.startsWith(CACHE_PREFIX));
  const buckets: CacheBucket[] = [];
  let total = 0;
  for (const name of names) {
    const cache = await caches.open(name);
    const reqs = await cache.keys();
    let bytes = 0;
    for (const req of reqs) {
      const res = await cache.match(req);
      if (res) bytes += await responseSize(res);
    }
    const isDownload = DOWNLOAD_BUCKET_HINTS.some((h) => name.includes(h));
    buckets.push({ name, entries: reqs.length, bytes, isDownload });
    total += bytes;
  }
  return { total, buckets };
}

/* --------------------------- indexeddb usage ---------------------------- */
export async function indexedDbUsage(): Promise<IndexedDbUsage> {
  let outbox = 0;
  let keyval = 0;
  let outboxItems = 0;
  try {
    const items = await outboxAll();
    outboxItems = items.length;
    outbox = byteLength(JSON.stringify(items));
  } catch {
    /* ignore */
  }
  try {
    const entries = await kvEntries();
    keyval = byteLength(JSON.stringify(entries));
  } catch {
    /* ignore */
  }
  return { bytes: outbox + keyval, outbox, keyval, outboxItems };
}

/* ------------------------------ clearing -------------------------------- */
/** Clear all app caches. Pass keepShell to preserve the precached app shell. */
export async function clearCaches(opts: { keepShell?: boolean } = {}): Promise<number> {
  if (typeof caches === "undefined") return 0;
  const names = (await caches.keys()).filter((n) => n.startsWith(CACHE_PREFIX));
  let cleared = 0;
  for (const name of names) {
    if (opts.keepShell && name.includes("precache")) continue;
    if (await caches.delete(name)) cleared++;
  }
  return cleared;
}

/** Clear only "downloaded" content (cached images + pages) — easily regenerable. */
export async function clearDownloads(): Promise<number> {
  if (typeof caches === "undefined") return 0;
  const names = await caches.keys();
  let cleared = 0;
  for (const name of names) {
    if (name.startsWith(CACHE_PREFIX) && DOWNLOAD_BUCKET_HINTS.some((h) => name.includes(h))) {
      if (await caches.delete(name)) cleared++;
    }
  }
  return cleared;
}

/* ------------------------------- export --------------------------------- */
export async function buildOfflineExport(): Promise<Record<string, unknown>> {
  const [outbox, keyval, est] = await Promise.all([
    outboxAll().catch(() => []),
    kvEntries().catch(() => []),
    estimateStorage(),
  ]);
  return {
    app: "hostel-management-system",
    exportedAt: new Date().toISOString(),
    storage: { usage: est.usage, quota: est.quota, persisted: est.persisted },
    outbox,
    keyval,
  };
}

/** Download all offline data (outbox + keyval) as a JSON file. */
export async function exportOfflineData(): Promise<void> {
  const data = await buildOfflineExport();
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `hostel-offline-export-${new Date().toISOString().slice(0, 10)}.json`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

/* -------------------------- quota monitoring ---------------------------- */
/**
 * Check quota and, if critically full, shed regenerable caches (downloads) to
 * recover space automatically. Returns what happened so callers can warn.
 */
export async function autoCleanupIfNeeded(): Promise<{
  ran: boolean;
  freedBuckets: number;
  before: StorageEstimateResult;
}> {
  const before = await estimateStorage();
  if (before.supported && before.level === "critical") {
    const freedBuckets = await clearDownloads();
    return { ran: true, freedBuckets, before };
  }
  return { ran: false, freedBuckets: 0, before };
}
