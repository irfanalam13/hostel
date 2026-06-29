/**
 * Minimal promise-based IndexedDB wrapper for the PWA.
 *
 * Schema (DB "hostel-pwa", version 2) — kept in sync with public/sw.js:
 *   - "outbox"  (keyPath "id")  queued offline mutations awaiting Background Sync
 *   - "keyval"  (out-of-line)   generic key/value store: preferences, drafts,
 *                               recently-viewed pages, cached API snapshots, etc.
 *   - "synclog" (keyPath "id")  append-only history of sync outcomes (v2)
 *
 * No third-party dependency — this is a thin wrapper so both the app and the
 * service worker can speak the same on-disk format.
 */

export const DB_NAME = "hostel-pwa";
export const DB_VERSION = 2;
export const OUTBOX_STORE = "outbox";
export const KEYVAL_STORE = "keyval";
export const SYNCLOG_STORE = "synclog";

let dbPromise: Promise<IDBDatabase> | null = null;

function isSupported(): boolean {
  return typeof indexedDB !== "undefined";
}

export function openDb(): Promise<IDBDatabase> {
  if (!isSupported()) return Promise.reject(new Error("IndexedDB is not available"));
  if (dbPromise) return dbPromise;
  dbPromise = new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(OUTBOX_STORE)) {
        db.createObjectStore(OUTBOX_STORE, { keyPath: "id" });
      }
      if (!db.objectStoreNames.contains(KEYVAL_STORE)) {
        db.createObjectStore(KEYVAL_STORE);
      }
      // v2: sync history log
      if (!db.objectStoreNames.contains(SYNCLOG_STORE)) {
        db.createObjectStore(SYNCLOG_STORE, { keyPath: "id" });
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
  return dbPromise;
}

function tx<T>(
  store: string,
  mode: IDBTransactionMode,
  run: (s: IDBObjectStore) => IDBRequest<T>,
): Promise<T> {
  return openDb().then(
    (db) =>
      new Promise<T>((resolve, reject) => {
        const t = db.transaction(store, mode);
        const req = run(t.objectStore(store));
        req.onsuccess = () => resolve(req.result);
        req.onerror = () => reject(req.error);
      }),
  );
}

/* ------------------------------- keyval API ----------------------------- */
export function kvGet<T = unknown>(key: string): Promise<T | undefined> {
  return tx<T>(KEYVAL_STORE, "readonly", (s) => s.get(key) as IDBRequest<T>);
}

export function kvSet(key: string, value: unknown): Promise<IDBValidKey> {
  return tx(KEYVAL_STORE, "readwrite", (s) => s.put(value, key));
}

export function kvDelete(key: string): Promise<undefined> {
  return tx(KEYVAL_STORE, "readwrite", (s) => s.delete(key) as IDBRequest<undefined>);
}

export function kvClear(): Promise<undefined> {
  return tx(KEYVAL_STORE, "readwrite", (s) => s.clear() as IDBRequest<undefined>);
}

/** All key/value pairs in the keyval store — used for export + size estimation. */
export async function kvEntries(): Promise<Array<{ key: string; value: unknown }>> {
  const db = await openDb();
  return new Promise((resolve, reject) => {
    const t = db.transaction(KEYVAL_STORE, "readonly");
    const store = t.objectStore(KEYVAL_STORE);
    const keysReq = store.getAllKeys();
    const valsReq = store.getAll();
    t.oncomplete = () => {
      const keys = keysReq.result as IDBValidKey[];
      const vals = valsReq.result as unknown[];
      resolve(keys.map((key, i) => ({ key: String(key), value: vals[i] })));
    };
    t.onerror = () => reject(t.error);
  });
}

/* ------------------------------- outbox API ----------------------------- */
export type OutboxItem = {
  id: string;
  url: string;
  method: string;
  headers: Record<string, string>;
  body: string | null;
  /** When true, the body is encrypted at rest (AES-GCM) — see pwa/crypto.ts.
   *  `body` is then null and the ciphertext lives in `bodyEnc`/`bodyIv`. */
  enc?: boolean;
  bodyEnc?: ArrayBuffer;
  bodyIv?: number[];
  createdAt: number;
  /** Optional idempotency key used to drop duplicate queued submissions. */
  dedupeKey?: string;
  /** Human label for the sync-status UI, e.g. "Create payment". */
  label?: string;
  /** Coarse entity type for grouping in the UI, e.g. "student", "payment". */
  entity?: string;
  /** Server idempotency key (sent as the Idempotency-Key header). */
  idempotencyKey?: string;
  /** sha256 of the body, for integrity verification before replay. */
  checksum?: string;
  /** Replay bookkeeping (v2). */
  attempts?: number;
  lastError?: string;
  /** Epoch ms; the SW skips the item until now >= nextRetryAt. */
  nextRetryAt?: number;
  /** "pending" (default) or "failed" (dead-lettered after max attempts / 4xx). */
  status?: "pending" | "failed";
};

export function outboxAll(): Promise<OutboxItem[]> {
  return tx<OutboxItem[]>(OUTBOX_STORE, "readonly", (s) => s.getAll() as IDBRequest<OutboxItem[]>);
}

export function outboxPut(item: OutboxItem): Promise<IDBValidKey> {
  return tx(OUTBOX_STORE, "readwrite", (s) => s.put(item));
}

export function outboxDelete(id: string): Promise<undefined> {
  return tx(OUTBOX_STORE, "readwrite", (s) => s.delete(id) as IDBRequest<undefined>);
}

export function outboxCount(): Promise<number> {
  return tx<number>(OUTBOX_STORE, "readonly", (s) => s.count());
}

/* ------------------------------- synclog API ---------------------------- */
export type SyncLogStatus = "queued" | "synced" | "duplicate" | "failed";

export type SyncLogEntry = {
  id: string;
  label: string;
  entity?: string;
  method: string;
  url: string;
  status: SyncLogStatus;
  httpStatus?: number;
  error?: string;
  /** Epoch ms when this outcome was recorded. */
  at: number;
};

/** Keep the history bounded so IndexedDB doesn't grow without limit. */
const SYNCLOG_LIMIT = 200;

export async function syncLogAdd(entry: SyncLogEntry): Promise<void> {
  await tx(SYNCLOG_STORE, "readwrite", (s) => s.put(entry));
  // Trim oldest entries beyond the cap (best effort).
  try {
    const all = await syncLogAll();
    if (all.length > SYNCLOG_LIMIT) {
      const excess = all
        .sort((a, b) => a.at - b.at)
        .slice(0, all.length - SYNCLOG_LIMIT);
      await Promise.all(
        excess.map((e) => tx(SYNCLOG_STORE, "readwrite", (s) => s.delete(e.id) as IDBRequest<undefined>))
      );
    }
  } catch {
    /* trimming is non-critical */
  }
}

export function syncLogAll(): Promise<SyncLogEntry[]> {
  return tx<SyncLogEntry[]>(SYNCLOG_STORE, "readonly", (s) => s.getAll() as IDBRequest<SyncLogEntry[]>);
}

export function syncLogClear(): Promise<undefined> {
  return tx(SYNCLOG_STORE, "readwrite", (s) => s.clear() as IDBRequest<undefined>);
}

export function syncLogCount(): Promise<number> {
  return tx<number>(SYNCLOG_STORE, "readonly", (s) => s.count());
}
