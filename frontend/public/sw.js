/* =============================================================================
 * Hostel Management System — Service Worker
 * -----------------------------------------------------------------------------
 * Enterprise service worker (hand-written, no build step) providing:
 *   - Versioned precache of the app shell + offline fallback
 *   - Per-resource runtime caching strategies
 *   - Navigation preload + network-first navigations with offline fallback
 *   - Safe updates (skipWaiting on demand + clients.claim)
 *   - Old-cache cleanup + image-cache trimming (expiration)
 *   - Background Sync: replays the IndexedDB "outbox" of queued mutations
 *   - Periodic Background Sync: refreshes notifications/notices/beds + update
 *     checks while the app is closed (Chromium, installed PWA)
 *   - Push notifications + notification click deep-linking
 *
 * SECURITY: cross-origin requests (the API lives on a different origin) are
 * NEVER intercepted or cached here — they pass straight through to the network,
 * so credentials, tokens and private API responses are never stored.
 * ========================================================================== */

const VERSION = "v3.3.0";
const PREFIX = "hms";
const PRECACHE = `${PREFIX}-precache-${VERSION}`;
const RUNTIME = `${PREFIX}-runtime-${VERSION}`;
const IMAGES = `${PREFIX}-images-${VERSION}`;
const PAGES = `${PREFIX}-pages-${VERSION}`;
const CURRENT_CACHES = [PRECACHE, RUNTIME, IMAGES, PAGES];

const OFFLINE_URL = "/offline";
const IMAGE_CACHE_LIMIT = 60;
const PAGE_CACHE_LIMIT = 30;

// Minimal shell precached on install. Hashed build assets are cached at runtime.
const PRECACHE_URLS = [
  OFFLINE_URL,
  "/manifest.webmanifest",
  "/icons/icon-192.png",
  "/icons/icon-512.png",
  "/icons/apple-touch-icon.png",
  "/favicon.ico",
];

const log = (...a) => console.log("[SW]", ...a);

/* ---- Cache-efficiency counters (flushed to clients for analytics) ------- */
let cacheHits = 0;
let cacheMisses = 0;
const CACHE_STATS_FLUSH_AT = 25;
function bumpCache(hit) {
  if (hit) cacheHits++;
  else cacheMisses++;
  if (cacheHits + cacheMisses >= CACHE_STATS_FLUSH_AT) flushCacheStats();
}
function flushCacheStats() {
  if (cacheHits === 0 && cacheMisses === 0) return;
  const hits = cacheHits;
  const misses = cacheMisses;
  cacheHits = 0;
  cacheMisses = 0;
  // broadcast() is a hoisted function declaration defined below.
  broadcast({ type: "CACHE_STATS", hits, misses });
}

/* ------------------------------- install -------------------------------- */
self.addEventListener("install", (event) => {
  event.waitUntil(
    (async () => {
      const cache = await caches.open(PRECACHE);
      // Use individual puts so one 404 can't abort the whole install.
      await Promise.all(
        PRECACHE_URLS.map(async (url) => {
          try {
            await cache.add(new Request(url, { cache: "reload" }));
          } catch (err) {
            log("precache miss", url, err);
          }
        }),
      );
      log("installed", VERSION);
      // Do NOT auto-skipWaiting: the page asks via postMessage so the user
      // controls when the update applies.
    })(),
  );
});

/* ------------------------------- activate ------------------------------- */
self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      if (self.registration.navigationPreload) {
        await self.registration.navigationPreload.enable();
      }
      const keys = await caches.keys();
      await Promise.all(
        keys
          .filter((k) => k.startsWith(PREFIX) && !CURRENT_CACHES.includes(k))
          .map((k) => {
            log("deleting old cache", k);
            return caches.delete(k);
          }),
      );
      await self.clients.claim();
      log("activated", VERSION);
    })(),
  );
});

/* ------------------------------- messages ------------------------------- */
self.addEventListener("message", (event) => {
  // HARDENING: only trust postMessage from a same-origin window/worker. A
  // cross-origin or opaque sender must never be able to drive the SW.
  if (event.origin && event.origin !== self.location.origin) return;
  const src = event.source;
  try {
    if (src && src.url && new URL(src.url).origin !== self.location.origin) return;
  } catch {
    return;
  }

  const data = event.data || {};
  if (data.type === "SKIP_WAITING") self.skipWaiting();
  else if (data.type === "GET_VERSION") event.ports[0]?.postMessage({ version: VERSION });
  else if (data.type === "FLUSH_OUTBOX") event.waitUntil(flushOutbox());
});

/* -------------------------------- fetch --------------------------------- */
self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Only ever handle same-origin GET. Everything else (API calls on another
  // origin, POST/PUT/PATCH/DELETE, hot-reload sockets) goes straight to network.
  if (request.method !== "GET") return;
  if (url.origin !== self.location.origin) return;
  if (url.pathname.startsWith("/_next/webpack-hmr")) return;

  if (request.mode === "navigate") {
    event.respondWith(handleNavigation(event));
    return;
  }

  const dest = request.destination;
  if (dest === "image") {
    event.respondWith(staleWhileRevalidate(request, IMAGES, IMAGE_CACHE_LIMIT));
  } else if (dest === "font" || url.pathname.startsWith("/_next/static/")) {
    // Content-hashed build output + fonts are immutable → cache-first.
    event.respondWith(cacheFirst(request, RUNTIME));
  } else {
    // styles, scripts and anything else same-origin → stale-while-revalidate.
    event.respondWith(staleWhileRevalidate(request, RUNTIME));
  }
});

/* --------------------------- caching strategies ------------------------- */
async function cacheFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);
  if (cached) {
    bumpCache(true);
    return cached;
  }
  try {
    const res = await fetch(request);
    if (res && res.ok) cache.put(request, res.clone());
    bumpCache(false);
    return res;
  } catch {
    return cached || Response.error();
  }
}

async function staleWhileRevalidate(request, cacheName, limit) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);
  const network = fetch(request)
    .then((res) => {
      if (res && res.ok) {
        cache.put(request, res.clone());
        if (limit) trimCache(cacheName, limit);
      }
      return res;
    })
    .catch(() => null);
  const result = cached || (await network) || Response.error();
  bumpCache(!!cached); // served from cache → hit; had to wait on network → miss
  return result;
}

async function handleNavigation(event) {
  const { request } = event;
  const cache = await caches.open(PAGES);
  try {
    // navigation preload gives us a head start on the network request
    const preload = await event.preloadResponse;
    const network = preload || (await fetch(request));
    // HARDENING: never persist a navigation the server marked private/no-store,
    // and only cache first-party ("basic") responses — so an authenticated page
    // the backend doesn't want stored never lands in the cache.
    const cc = (network && network.headers.get("Cache-Control")) || "";
    const cacheable = network && network.ok && network.type === "basic" && !/no-store|private/i.test(cc);
    if (cacheable) {
      cache.put(request, network.clone());
      trimCache(PAGES, PAGE_CACHE_LIMIT);
    }
    bumpCache(false); // navigation served from the network
    return network;
  } catch {
    const cached = await cache.match(request);
    if (cached) {
      bumpCache(true); // served a cached page while offline
      return cached;
    }
    bumpCache(true); // served the offline fallback from cache
    const offline = await caches.match(OFFLINE_URL);
    return (
      offline ||
      new Response("You are offline.", {
        status: 503,
        headers: { "Content-Type": "text/plain" },
      })
    );
  }
}

async function trimCache(cacheName, maxEntries) {
  const cache = await caches.open(cacheName);
  const keys = await cache.keys();
  if (keys.length <= maxEntries) return;
  // FIFO eviction of the oldest entries.
  for (let i = 0; i < keys.length - maxEntries; i++) {
    await cache.delete(keys[i]);
  }
}

/* ----------------------------- background sync -------------------------- */
self.addEventListener("sync", (event) => {
  if (event.tag === "hms-outbox-sync") {
    event.waitUntil(flushOutbox());
  }
});

// IndexedDB access (the SW can't import app modules, so this mirrors the schema
// declared in src/shared/pwa/db.ts — keep DB_VERSION + stores in sync).
const DB_NAME = "hostel-pwa";
const DB_VERSION = 2;
const OUTBOX_STORE = "outbox";
const SYNCLOG_STORE = "synclog";

const MAX_ATTEMPTS = 8;
const SYNCLOG_LIMIT = 200;

function openDb() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(OUTBOX_STORE)) {
        db.createObjectStore(OUTBOX_STORE, { keyPath: "id" });
      }
      if (!db.objectStoreNames.contains("keyval")) {
        db.createObjectStore("keyval");
      }
      if (!db.objectStoreNames.contains(SYNCLOG_STORE)) {
        db.createObjectStore(SYNCLOG_STORE, { keyPath: "id" });
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

function idbGetAll(db, store) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(store, "readonly");
    const req = tx.objectStore(store).getAll();
    req.onsuccess = () => resolve(req.result || []);
    req.onerror = () => reject(req.error);
  });
}

function idbPut(db, store, value) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(store, "readwrite");
    tx.objectStore(store).put(value);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

function idbDelete(db, store, key) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(store, "readwrite");
    tx.objectStore(store).delete(key);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

let logCounter = 0;
function makeLogId() {
  logCounter = (logCounter + 1) % 1000000;
  return `${Date.now()}-${logCounter}`;
}

async function addSyncLog(db, entry) {
  try {
    await idbPut(db, SYNCLOG_STORE, { id: makeLogId(), at: Date.now(), ...entry });
    // Trim oldest entries beyond the cap.
    const all = await idbGetAll(db, SYNCLOG_STORE);
    if (all.length > SYNCLOG_LIMIT) {
      const excess = all.sort((a, b) => a.at - b.at).slice(0, all.length - SYNCLOG_LIMIT);
      for (const e of excess) await idbDelete(db, SYNCLOG_STORE, e.id);
    }
  } catch {
    /* logging is best-effort */
  }
}

// Exponential backoff (capped) for transient failures.
function backoffMs(attempts) {
  return Math.min(5 * 60 * 1000, 1000 * Math.pow(2, attempts)); // 2s,4s,8s … cap 5min
}

function logEntryFor(item, status, httpStatus, error) {
  return {
    label: item.label || `${item.method} ${item.url}`,
    entity: item.entity,
    method: item.method,
    url: item.url,
    status,
    httpStatus,
    error,
  };
}

// Decrypt an outbox item's body (encrypted at rest by the app — see
// src/shared/pwa/crypto.ts). The non-extractable AES-GCM key is read from the
// shared keyval store; the SW only ever reads it, never generates it.
async function decryptOutboxBody(item) {
  const key = await kvGetSW("__outbox_crypto_key__");
  if (!key) throw new Error("outbox key unavailable");
  const buf = await crypto.subtle.decrypt(
    { name: "AES-GCM", iv: new Uint8Array(item.bodyIv) },
    key,
    item.bodyEnc,
  );
  return new TextDecoder().decode(buf);
}

// Replay queued mutations oldest-first. Each item is resolved independently:
//   2xx                  → done (delete, log "synced")
//   409 idempotent replay → already applied server-side (delete, log "duplicate")
//   other 4xx            → non-retryable → dead-letter (status:"failed", log "failed")
//   5xx / network        → retry with backoff; after MAX_ATTEMPTS → dead-letter
async function flushOutbox() {
  const db = await openDb();
  const now = Date.now();
  const items = (await idbGetAll(db, OUTBOX_STORE))
    .filter((i) => i.status !== "failed")
    .filter((i) => !i.nextRetryAt || i.nextRetryAt <= now)
    .sort((a, b) => a.createdAt - b.createdAt);

  let synced = 0;
  let failed = 0;
  let changed = false;

  for (const item of items) {
    // Resolve the (possibly encrypted-at-rest) body before sending.
    let body = item.body;
    if (item.enc && item.bodyEnc) {
      try {
        body = await decryptOutboxBody(item);
      } catch {
        item.status = "failed";
        item.lastError = "decrypt failed";
        await idbPut(db, OUTBOX_STORE, item);
        await addSyncLog(db, logEntryFor(item, "failed", undefined, "decrypt failed"));
        changed = true;
        failed++;
        continue;
      }
    }

    let res;
    try {
      res = await fetch(item.url, {
        method: item.method,
        headers: item.headers,
        body,
        credentials: "include",
      });
    } catch {
      // Offline again — back off and retry this item on the next sync.
      item.attempts = (item.attempts || 0) + 1;
      item.lastError = "network error";
      if (item.attempts >= MAX_ATTEMPTS) {
        item.status = "failed";
        await idbPut(db, OUTBOX_STORE, item);
        await addSyncLog(db, logEntryFor(item, "failed", undefined, "network error (max retries)"));
        changed = true;
        failed++;
        continue;
      }
      item.nextRetryAt = now + backoffMs(item.attempts);
      await idbPut(db, OUTBOX_STORE, item);
      continue;
    }

    if (res.ok) {
      await idbDelete(db, OUTBOX_STORE, item.id);
      await addSyncLog(db, logEntryFor(item, "synced", res.status));
      synced++;
      changed = true;
    } else if (res.status === 409) {
      // Idempotent replay / already-applied → treat as a resolved duplicate.
      await idbDelete(db, OUTBOX_STORE, item.id);
      await addSyncLog(db, logEntryFor(item, "duplicate", 409));
      changed = true;
    } else if (res.status >= 400 && res.status < 500) {
      // Validation/permission error — replaying won't help. Dead-letter it.
      let detail = `HTTP ${res.status}`;
      try {
        const data = await res.clone().json();
        detail = data.detail || data.message || JSON.stringify(data).slice(0, 200);
      } catch {
        /* keep generic detail */
      }
      item.status = "failed";
      item.lastError = detail;
      await idbPut(db, OUTBOX_STORE, item);
      await addSyncLog(db, logEntryFor(item, "failed", res.status, detail));
      changed = true;
      failed++;
    } else {
      // 5xx — server trouble; retry with backoff.
      item.attempts = (item.attempts || 0) + 1;
      item.lastError = `HTTP ${res.status}`;
      if (item.attempts >= MAX_ATTEMPTS) {
        item.status = "failed";
        await idbPut(db, OUTBOX_STORE, item);
        await addSyncLog(db, logEntryFor(item, "failed", res.status, `server error (max retries)`));
        failed++;
      } else {
        item.nextRetryAt = now + backoffMs(item.attempts);
        await idbPut(db, OUTBOX_STORE, item);
      }
      changed = true;
    }
  }

  if (synced > 0 || failed > 0) {
    await broadcast({ type: "OUTBOX_SYNCED", count: synced, failed });
  }
  if (changed) await broadcast({ type: "SYNC_LOG_UPDATED" });
  return synced;
}

async function broadcast(msg) {
  const clients = await self.clients.matchAll({ includeUncontrolled: true, type: "window" });
  for (const c of clients) c.postMessage(msg);
}

/* ----------------------------- push messages --------------------------- */
self.addEventListener("push", (event) => {
  let payload = {};
  try {
    payload = event.data ? event.data.json() : {};
  } catch {
    payload = { title: "Hostel MS", body: event.data ? event.data.text() : "" };
  }
  const title = payload.title || "Hostel Management System";
  const options = {
    body: payload.body || "",
    icon: payload.icon || "/icons/icon-192.png",
    badge: "/icons/favicon-48.png",
    tag: payload.tag,
    data: { url: payload.url || "/dashboard", ...(payload.data || {}) },
    requireInteraction: !!payload.requireInteraction,
    timestamp: payload.timestamp,
  };
  event.waitUntil(
    (async () => {
      await self.registration.showNotification(title, options);
      await broadcast({ type: "PUSH_RECEIVED", tag: payload.tag });
    })(),
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const target = (event.notification.data && event.notification.data.url) || "/dashboard";
  event.waitUntil(
    (async () => {
      await broadcast({ type: "PUSH_OPEN", url: target });
      const clients = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
      for (const client of clients) {
        // Focus an existing tab if one is already open.
        if ("focus" in client) {
          await client.focus();
          if ("navigate" in client) client.navigate(target).catch(() => {});
          return;
        }
      }
      if (self.clients.openWindow) await self.clients.openWindow(target);
    })(),
  );
});

/* ----------------------- periodic background sync ----------------------- */
/*
 * Runs even when the app is closed (Chromium + installed PWA + permission). The
 * browser throttles these heavily (hours apart), so they're for "catch up while
 * away": keep the badge fresh, alert on new announcements, refresh availability,
 * and pull SW updates. Tags + cadence are declared in
 * src/shared/pwa/backgroundTasks.ts. Foreground refresh is handled in-page.
 */
self.addEventListener("periodicsync", (event) => {
  switch (event.tag) {
    case "check-updates":
      event.waitUntil(self.registration.update());
      break;
    case "refresh-notifications":
      event.waitUntil(periodicRefreshNotifications());
      break;
    case "refresh-announcements":
      event.waitUntil(periodicRefreshAnnouncements());
      break;
    case "refresh-room-availability":
      event.waitUntil(periodicRefreshRoomAvailability());
      break;
    default:
      break;
  }
});

/* ---- keyval access (shared store written by the app via db.ts) ---------- */
function kvGetSW(key) {
  return openDb().then(
    (db) =>
      new Promise((resolve) => {
        const req = db.transaction("keyval", "readonly").objectStore("keyval").get(key);
        req.onsuccess = () => resolve(req.result);
        req.onerror = () => resolve(undefined);
      }),
  );
}

function kvSetSW(key, value) {
  return openDb().then(
    (db) =>
      new Promise((resolve) => {
        const tx = db.transaction("keyval", "readwrite");
        tx.objectStore("keyval").put(value, key);
        tx.oncomplete = () => resolve();
        tx.onerror = () => resolve();
      }),
  );
}

// Mirror the app's response envelope unwrap ({success, data, meta} → data).
function unwrapEnvelope(body) {
  if (body && typeof body === "object" && typeof body.success === "boolean" && "data" in body) {
    return body.data;
  }
  return body;
}

// Authenticated GET against the cross-origin API. Auth rides in httpOnly
// cookies (credentials:"include"); on a 401 we attempt one cookie refresh and
// retry, mirroring the app's apiClient. Returns the unwrapped JSON or null.
async function bgFetch(path) {
  const cfg = await kvGetSW("bg-config");
  if (!cfg || !cfg.apiBase) return null;
  const base = String(cfg.apiBase).replace(/\/+$/, "");
  const headers = {};
  if (cfg.hostelCode) headers["X-Hostel-Code"] = cfg.hostelCode;

  const doFetch = () => fetch(base + path, { credentials: "include", headers, cache: "no-store" });

  let res;
  try {
    res = await doFetch();
  } catch {
    return null; // offline / network error
  }
  if (res.status === 401) {
    try {
      const r = await fetch(base + "/auth/token/refresh/", {
        method: "POST",
        credentials: "include",
        cache: "no-store",
      });
      if (r.ok) res = await doFetch();
    } catch {
      /* refresh failed — give up quietly */
    }
  }
  if (!res || !res.ok) return null;
  try {
    return unwrapEnvelope(await res.json());
  } catch {
    return null;
  }
}

function canNotify() {
  return typeof self.Notification !== "undefined" && self.Notification.permission === "granted";
}

async function periodicRefreshNotifications() {
  const data = await bgFetch("/notifications/unread_count/");
  if (!data) return;
  const unread = typeof data.unread === "number" ? data.unread : 0;
  await kvSetSW("bg-marker-notifications", unread);
  // Keep an open tab's badge fresh. We deliberately don't raise a system
  // notification here — Web Push owns real-time alerting, so this would double up.
  await broadcast({ type: "BG_REFRESH", task: "refresh-notifications", unread });
}

async function periodicRefreshAnnouncements() {
  const data = await bgFetch("/notices/");
  const list = Array.isArray(data) ? data : (data && data.results) || [];
  await broadcast({ type: "BG_REFRESH", task: "refresh-announcements" });
  if (!list.length) return;

  // Newest by published_at (fallback to id). Alert once if it changed while away.
  const newest = list.reduce((a, b) =>
    String(b.published_at || b.id || "") > String(a.published_at || a.id || "") ? b : a,
  );
  const key = String(newest.published_at || newest.id || "");
  const prev = (await kvGetSW("bg-marker-announcements")) || "";
  await kvSetSW("bg-marker-announcements", key);

  if (prev && key && key !== prev && canNotify()) {
    try {
      await self.registration.showNotification("New announcement", {
        body: newest.title || "A new notice was posted.",
        icon: "/icons/icon-192.png",
        badge: "/icons/favicon-48.png",
        tag: "announcement-" + key,
        data: { url: "/notices" },
      });
    } catch {
      /* notification is best-effort */
    }
  }
}

async function periodicRefreshRoomAvailability() {
  // The owner dashboard carries a compact bed summary — cheaper than the full
  // bed list. Cache it so the next open paints instantly, and nudge open tabs.
  const data = await bgFetch("/dashboard/owner/");
  if (data && data.beds) {
    await kvSetSW("bg-cache-room-availability", { beds: data.beds, at: Date.now() });
  }
  await broadcast({ type: "BG_REFRESH", task: "refresh-room-availability" });
}
