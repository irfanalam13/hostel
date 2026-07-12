/**
 * Sync history — a bounded, append-only log of offline-write outcomes
 * (queued → synced / duplicate / failed). Written by both the app (on enqueue
 * and immediate success) and the service worker (on replay).
 */
import {
  type SyncLogEntry,
  type SyncLogStatus,
  syncLogAdd,
  syncLogAll,
  syncLogClear,
  syncLogCount,
} from "./db";

export type { SyncLogEntry, SyncLogStatus };

let counter = 0;
function makeId(): string {
  counter = (counter + 1) % 1_000_000;
  return `${Date.now()}-${counter}-${performance.now().toString(36)}`;
}

export async function logSync(entry: Omit<SyncLogEntry, "id" | "at"> & { at?: number }): Promise<void> {
  try {
    await syncLogAdd({ id: makeId(), at: entry.at ?? Date.now(), ...entry });
  } catch {
    /* logging must never break the caller */
  }
}

/** Most-recent-first history for the Sync Center UI. */
export async function syncHistory(): Promise<SyncLogEntry[]> {
  const all = await syncLogAll().catch(() => [] as SyncLogEntry[]);
  return all.sort((a, b) => b.at - a.at);
}

export function clearSyncHistory(): Promise<undefined> {
  return syncLogClear();
}

export function syncHistoryCount(): Promise<number> {
  return syncLogCount().catch(() => 0);
}
