/**
 * Offline write queue ("outbox").
 *
 * When a mutating request (POST/PUT/PATCH/DELETE) can't reach the network, it is
 * serialized into IndexedDB and a Background Sync is registered. The service
 * worker's "sync" handler (public/sw.js → flushOutbox) replays the queue in
 * order once connectivity returns. Where Background Sync is unsupported (Safari/
 * Firefox), we fall back to flushing on the next "online" event.
 *
 * De-duplication: callers may pass a `dedupeKey` so an identical retry doesn't
 * enqueue twice (prevents double submissions).
 */
import { OutboxItem, outboxAll, outboxCount, outboxDelete, outboxPut } from "./db";
import { encryptString } from "./crypto";

export type { OutboxItem };

const SYNC_TAG = "hms-outbox-sync";

let counter = 0;
function makeId(): string {
  // Monotonic-ish id without Math.random/Date dependency edge cases.
  counter = (counter + 1) % 1_000_000;
  return `${Date.now()}-${counter}-${performance.now().toString(36)}`;
}

export type QueueInput = {
  url: string;
  method: string;
  headers?: Record<string, string>;
  body?: string | null;
  dedupeKey?: string;
  label?: string;
};

/** Add a request to the outbox and ask the platform to sync it later. */
export async function enqueueRequest(input: QueueInput): Promise<OutboxItem> {
  if (input.dedupeKey) {
    const existing = await outboxAll();
    const dupe = existing.find((i) => i.dedupeKey === input.dedupeKey);
    if (dupe) return dupe;
  }
  const item: OutboxItem = {
    id: makeId(),
    url: input.url,
    method: input.method.toUpperCase(),
    headers: input.headers ?? {},
    body: input.body ?? null,
    createdAt: Date.now(),
    dedupeKey: input.dedupeKey,
    label: input.label,
  };

  // Encrypt the body at rest where possible. The SW decrypts it on replay
  // (public/sw.js → decryptOutboxBody). If WebCrypto is unavailable we fall back
  // to storing plaintext so offline sync still works.
  if (item.body) {
    const blob = await encryptString(item.body).catch(() => null);
    if (blob) {
      item.enc = true;
      item.bodyEnc = blob.data;
      item.bodyIv = blob.iv;
      item.body = null;
    }
  }

  await outboxPut(item);
  await requestSync();
  return item;
}

export function pendingCount(): Promise<number> {
  return outboxCount().catch(() => 0);
}

export function pendingItems(): Promise<OutboxItem[]> {
  return outboxAll().catch(() => []);
}

/** Register a one-off Background Sync, falling back to an immediate flush. */
export async function requestSync(): Promise<void> {
  try {
    const reg = await navigator.serviceWorker?.ready;
    // SyncManager is not in the TS DOM lib by default.
    const sync = (reg as unknown as { sync?: { register(tag: string): Promise<void> } })?.sync;
    if (sync) {
      await sync.register(SYNC_TAG);
      return;
    }
  } catch {
    /* fall through to manual flush */
  }
  // No Background Sync support → ask the SW to flush now (best effort).
  flushNow();
}

/** Ask the active service worker to drain the outbox immediately. */
export function flushNow(): void {
  navigator.serviceWorker?.controller?.postMessage({ type: "FLUSH_OUTBOX" });
}

/** Remove a queued item (e.g. user cancels a pending action). */
export function discard(id: string): Promise<void> {
  return outboxDelete(id).then(() => undefined);
}

/** Items that were dead-lettered (persistent 4xx or max retries exceeded). */
export async function failedItems(): Promise<OutboxItem[]> {
  const all = await pendingItems();
  return all.filter((i) => i.status === "failed");
}

/** Items still awaiting sync (not dead-lettered). */
export async function activeItems(): Promise<OutboxItem[]> {
  const all = await pendingItems();
  return all.filter((i) => i.status !== "failed");
}

/**
 * Re-queue a dead-lettered item: clear its failed state + retry bookkeeping and
 * ask the platform to sync again. Used by the Sync Center "Retry" action.
 */
export async function retryItem(id: string): Promise<void> {
  const all = await pendingItems();
  const item = all.find((i) => i.id === id);
  if (!item) return;
  item.status = "pending";
  item.attempts = 0;
  item.lastError = "";
  item.nextRetryAt = 0;
  await outboxPut(item);
  await requestSync();
}

/**
 * Wire up automatic flushing when connectivity returns. Call once at startup.
 * Returns a cleanup function.
 */
export function initOutboxAutoFlush(): () => void {
  const onOnline = () => {
    void requestSync();
  };
  window.addEventListener("online", onOnline);
  // Also try once on load in case a sync was missed.
  void requestSync();
  return () => window.removeEventListener("online", onOnline);
}
