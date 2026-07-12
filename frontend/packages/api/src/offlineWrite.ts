/**
 * offlineWrite — the single entry point for offline-capable mutations.
 *
 * It wraps apiFetch with everything the offline-sync pipeline needs:
 *   - a per-action Idempotency-Key (so a replay after a lost ack can't create a
 *     duplicate — the backend IdempotencyMiddleware returns the original result);
 *   - an X-Payload-Checksum (sha256 of the body) for server-side integrity checks;
 *   - offlineQueue:true so a network failure persists the request to the IndexedDB
 *     outbox for Background Sync (see shared/pwa/outbox.ts + public/sw.js);
 *   - a sync-history entry on success / queue.
 *
 * When offline, it rejects with OfflineQueuedError — callers should treat that as
 * "saved, will sync" rather than a hard failure.
 */
import { apiFetch, OfflineQueuedError } from "./apiClient";
import { logSync } from "@hostel/pwa/synclog";

export type OfflineWriteOptions = {
  method?: "POST" | "PUT" | "PATCH" | "DELETE";
  /** Human label shown in the Sync Center, e.g. "Register student". */
  label: string;
  /** Coarse grouping, e.g. "student", "payment", "attendance". */
  entity?: string;
};

function uuid(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID();
  // Fallback for older browsers.
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

async function sha256Hex(text: string): Promise<string> {
  try {
    const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
    return Array.from(new Uint8Array(buf))
      .map((b) => b.toString(16).padStart(2, "0"))
      .join("");
  } catch {
    return ""; // integrity header is best-effort; skip if SubtleCrypto unavailable
  }
}

export async function offlineWrite<T = unknown>(
  path: string,
  body: unknown,
  opts: OfflineWriteOptions
): Promise<T> {
  const method = opts.method ?? "POST";
  const serialized = body === undefined ? "" : JSON.stringify(body);
  const idempotencyKey = uuid();
  const checksum = await sha256Hex(serialized);

  const headers: Record<string, string> = { "Idempotency-Key": idempotencyKey };
  if (checksum) headers["X-Payload-Checksum"] = checksum;

  try {
    const data = await apiFetch<T>(path, {
      method,
      body: serialized || undefined,
      headers,
      offlineQueue: true,
      dedupeKey: idempotencyKey,
      queueLabel: opts.label,
    });
    await logSync({ label: opts.label, entity: opts.entity, method, url: path, status: "synced", httpStatus: 200 });
    return data;
  } catch (err) {
    if (err instanceof OfflineQueuedError) {
      await logSync({ label: opts.label, entity: opts.entity, method, url: path, status: "queued" });
    }
    throw err;
  }
}
