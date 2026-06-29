"use client";

import { useCallback, useEffect, useState } from "react";
import { usePwa } from "@/shared/providers/PwaProvider";
import {
  activeItems,
  discard,
  failedItems,
  flushNow,
  retryItem,
  type OutboxItem,
} from "@/shared/pwa/outbox";
import { clearSyncHistory, syncHistory, type SyncLogEntry } from "@/shared/pwa/synclog";
import { Button } from "@/shared/ui/Button";
import { Card } from "@/shared/ui/Card";
import { useToast } from "@/shared/ui/toast/ToastProvider";

function timeAgo(ms: number) {
  const diff = Date.now() - ms;
  const s = Math.floor(diff / 1000);
  if (s < 60) return "just now";
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

const STATUS_STYLE: Record<SyncLogEntry["status"], string> = {
  queued: "bg-amber-500/10 text-amber-600",
  synced: "bg-emerald-500/10 text-emerald-600",
  duplicate: "bg-blue-500/10 text-blue-600",
  failed: "bg-red-500/10 text-red-600",
};

export function SyncCenter() {
  const { isOnline, pendingSync, refreshPending } = usePwa();
  const toast = useToast();
  const [pending, setPending] = useState<OutboxItem[]>([]);
  const [failed, setFailed] = useState<OutboxItem[]>([]);
  const [history, setHistory] = useState<SyncLogEntry[]>([]);

  const reload = useCallback(async () => {
    const [a, f, h] = await Promise.all([activeItems(), failedItems(), syncHistory()]);
    setPending(a);
    setFailed(f);
    setHistory(h);
    refreshPending();
  }, [refreshPending]);

  useEffect(() => {
    reload();
    const onUpdate = () => reload();
    window.addEventListener("sync-log-updated", onUpdate);
    return () => window.removeEventListener("sync-log-updated", onUpdate);
  }, [reload]);

  async function onDiscard(id: string) {
    await discard(id);
    toast.info("Removed from queue.");
    reload();
  }

  async function onRetry(id: string) {
    await retryItem(id);
    toast.info("Re-queued for sync.");
    reload();
  }

  async function onSyncNow() {
    flushNow();
    toast.info("Sync requested.");
    setTimeout(reload, 1500);
  }

  async function onClearHistory() {
    await clearSyncHistory();
    setHistory([]);
  }

  return (
    <div className="space-y-4">
      {/* Status header */}
      <Card className="!p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span
              className={`h-2.5 w-2.5 rounded-full ${isOnline ? "bg-emerald-500" : "bg-red-500"}`}
            />
            <span className="font-medium">{isOnline ? "Online" : "Offline"}</span>
            <span className="text-sm text-[var(--muted)]">
              · {pendingSync} pending {failed.length ? `· ${failed.length} failed` : ""}
            </span>
          </div>
          <Button size="sm" variant="secondary" onClick={onSyncNow} disabled={!isOnline || pending.length === 0}>
            Sync now
          </Button>
        </div>
      </Card>

      {/* Pending queue */}
      <Card>
        <div className="mb-3 text-sm font-semibold">Pending ({pending.length})</div>
        {pending.length === 0 ? (
          <div className="text-sm text-[var(--muted)]">Nothing waiting to sync.</div>
        ) : (
          <div className="divide-y divide-[var(--border)]">
            {pending.map((item) => (
              <div key={item.id} className="flex items-center justify-between gap-3 py-2 text-sm">
                <div>
                  <div className="font-medium">{item.label || `${item.method} ${item.url}`}</div>
                  <div className="text-xs text-[var(--muted)]">
                    {timeAgo(item.createdAt)}
                    {item.attempts ? ` · ${item.attempts} attempt(s)` : ""}
                  </div>
                </div>
                <Button size="sm" variant="ghost" onClick={() => onDiscard(item.id)}>
                  Discard
                </Button>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Failed / dead-lettered */}
      {failed.length > 0 && (
        <Card>
          <div className="mb-3 text-sm font-semibold text-red-600">Failed ({failed.length})</div>
          <div className="divide-y divide-[var(--border)]">
            {failed.map((item) => (
              <div key={item.id} className="flex items-center justify-between gap-3 py-2 text-sm">
                <div className="min-w-0">
                  <div className="font-medium">{item.label || `${item.method} ${item.url}`}</div>
                  <div className="truncate text-xs text-red-500">{item.lastError || "Failed to sync"}</div>
                </div>
                <div className="flex shrink-0 gap-1">
                  <Button size="sm" variant="secondary" onClick={() => onRetry(item.id)}>
                    Retry
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => onDiscard(item.id)}>
                    Discard
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* History */}
      <Card>
        <div className="mb-3 flex items-center justify-between">
          <div className="text-sm font-semibold">Sync history</div>
          {history.length > 0 && (
            <button onClick={onClearHistory} className="text-xs font-semibold text-[var(--accent)] hover:underline">
              Clear
            </button>
          )}
        </div>
        {history.length === 0 ? (
          <div className="text-sm text-[var(--muted)]">No sync activity yet.</div>
        ) : (
          <div className="max-h-80 divide-y divide-[var(--border)] overflow-y-auto">
            {history.map((e) => (
              <div key={e.id} className="flex items-center justify-between gap-3 py-2 text-sm">
                <div className="min-w-0">
                  <div className="truncate font-medium">{e.label}</div>
                  {e.error ? <div className="truncate text-xs text-red-500">{e.error}</div> : null}
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${STATUS_STYLE[e.status]}`}>
                    {e.status}
                  </span>
                  <span className="text-xs text-[var(--muted)]">{timeAgo(e.at)}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
