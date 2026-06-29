"use client";

import { useCallback, useEffect, useState } from "react";
import { useConfirm } from "@/shared/ui/ConfirmProvider";
import { useToast } from "@/shared/ui/toast/ToastProvider";
import {
  CacheUsage,
  IndexedDbUsage,
  StorageEstimateResult,
  cacheUsage,
  clearCaches,
  clearDownloads,
  estimateStorage,
  exportOfflineData,
  formatBytes,
  indexedDbUsage,
  requestPersistentStorage,
} from "@/shared/pwa/storage";

const LEVEL_COLOR: Record<string, string> = {
  ok: "var(--success)",
  warn: "var(--warning)",
  critical: "var(--error)",
};

function prettyBucket(name: string): string {
  // hms-images-v3.0.0 → "Images"
  const core = name.replace(/^hms-/, "").replace(/-v[\d.]+$/, "");
  return core.charAt(0).toUpperCase() + core.slice(1);
}

/**
 * Storage management panel: device-quota usage, cache + IndexedDB breakdown,
 * and controls to clear caches/downloads, export offline data, and enable
 * persistent storage. Drop into Settings.
 */
export function StorageCard() {
  const toast = useToast();
  const confirm = useConfirm();

  const [est, setEst] = useState<StorageEstimateResult | null>(null);
  const [cache, setCache] = useState<CacheUsage | null>(null);
  const [idb, setIdb] = useState<IndexedDbUsage | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [e, c, d] = await Promise.all([estimateStorage(), cacheUsage(), indexedDbUsage()]);
      setEst(e);
      setCache(c);
      setIdb(d);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const run = async (key: string, fn: () => Promise<void>) => {
    setBusy(key);
    try {
      await fn();
    } finally {
      setBusy(null);
    }
  };

  const onClearCache = () =>
    run("cache", async () => {
      const ok = await confirm({
        title: "Clear cache?",
        message:
          "This removes cached pages, images and assets. The app keeps working — content re-downloads when you next open it online.",
        confirmText: "Clear cache",
        danger: true,
      });
      if (!ok) return;
      const n = await clearCaches({ keepShell: true });
      toast.success(`Cleared ${n} cache bucket${n === 1 ? "" : "s"}.`);
      await refresh();
    });

  const onClearDownloads = () =>
    run("downloads", async () => {
      const ok = await confirm({
        title: "Clear downloads?",
        message: "Removes cached images and previously visited pages. Unsynced changes are kept.",
        confirmText: "Clear downloads",
        danger: true,
      });
      if (!ok) return;
      const n = await clearDownloads();
      toast.success(n ? `Cleared ${n} download cache${n === 1 ? "" : "s"}.` : "Nothing to clear.");
      await refresh();
    });

  const onExport = () =>
    run("export", async () => {
      await exportOfflineData();
      toast.success("Offline data exported.");
    });

  const onPersist = () =>
    run("persist", async () => {
      const granted = await requestPersistentStorage();
      toast[granted ? "success" : "info"](
        granted ? "Persistent storage enabled." : "The browser declined persistent storage.",
      );
      await refresh();
    });

  const percent = est ? Math.round(est.percent * 100) : 0;
  const level = est?.level ?? "ok";
  const barColor = LEVEL_COLOR[level];

  return (
    <div className="rounded-2xl border border-[var(--border)] bg-[var(--card)] p-4 space-y-4 text-sm">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-[var(--foreground)]">Storage &amp; offline data</h2>
        <button
          onClick={refresh}
          disabled={loading}
          className="text-xs font-medium text-[var(--accent)] hover:underline disabled:opacity-50"
        >
          {loading ? "Refreshing…" : "Refresh"}
        </button>
      </div>

      {/* Storage warning */}
      {est?.supported && level !== "ok" && (
        <div
          className="rounded-xl px-3 py-2 text-xs font-medium"
          style={{ backgroundColor: `${barColor}1a`, color: barColor }}
        >
          {level === "critical"
            ? "Storage is almost full. Clear downloads to free space."
            : "Storage is getting full. Consider clearing cached downloads."}
        </div>
      )}

      {/* Device quota bar */}
      {est?.supported ? (
        <div className="space-y-1.5">
          <div className="flex justify-between text-[var(--muted)]">
            <span>Device storage used</span>
            <span className="tabular-nums">
              {formatBytes(est.usage)} / {formatBytes(est.quota)} ({percent}%)
            </span>
          </div>
          <div className="h-2.5 w-full overflow-hidden rounded-full bg-[var(--background-secondary)]">
            <div
              className="h-full rounded-full transition-all"
              style={{ width: `${Math.max(percent, 1)}%`, backgroundColor: barColor }}
            />
          </div>
          <div className="flex justify-between text-[11px] text-[var(--muted)]">
            <span>{est.persisted ? "Persistent (won't be auto-evicted)" : "Best-effort (may be evicted)"}</span>
            {!est.persisted && (
              <button
                onClick={onPersist}
                disabled={busy === "persist"}
                className="font-medium text-[var(--accent)] hover:underline disabled:opacity-50"
              >
                Enable persistent
              </button>
            )}
          </div>
        </div>
      ) : (
        <p className="text-[var(--muted)]">Storage estimation isn&apos;t supported in this browser.</p>
      )}

      {/* Breakdown */}
      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-xl border border-[var(--border)] p-3">
          <p className="text-[var(--muted)]">Cache storage</p>
          <p className="text-lg font-semibold text-[var(--foreground)] tabular-nums">
            {formatBytes(cache?.total ?? 0)}
          </p>
          <p className="text-[11px] text-[var(--muted)]">
            {cache?.buckets.reduce((n, b) => n + b.entries, 0) ?? 0} items
          </p>
        </div>
        <div className="rounded-xl border border-[var(--border)] p-3">
          <p className="text-[var(--muted)]">App data (IndexedDB)</p>
          <p className="text-lg font-semibold text-[var(--foreground)] tabular-nums">
            {formatBytes(idb?.bytes ?? 0)}
          </p>
          <p className="text-[11px] text-[var(--muted)]">{idb?.outboxItems ?? 0} queued change(s)</p>
        </div>
      </div>

      {/* Per-bucket list */}
      {cache && cache.buckets.length > 0 && (
        <ul className="space-y-1 text-xs">
          {cache.buckets.map((b) => (
            <li key={b.name} className="flex justify-between text-[var(--muted)]">
              <span>
                {prettyBucket(b.name)}
                {b.isDownload && <span className="ml-1 text-[10px] opacity-70">(download)</span>}
              </span>
              <span className="tabular-nums">
                {formatBytes(b.bytes)} · {b.entries}
              </span>
            </li>
          ))}
        </ul>
      )}

      {/* Actions */}
      <div className="flex flex-wrap gap-2 pt-1">
        <button
          onClick={onClearDownloads}
          disabled={!!busy}
          className="rounded-xl border border-[var(--border)] px-3 py-2 text-xs font-medium transition hover:bg-[var(--background-secondary)] disabled:opacity-50"
        >
          {busy === "downloads" ? "Clearing…" : "Clear downloads"}
        </button>
        <button
          onClick={onClearCache}
          disabled={!!busy}
          className="rounded-xl border border-[var(--border)] px-3 py-2 text-xs font-medium transition hover:bg-[var(--background-secondary)] disabled:opacity-50"
        >
          {busy === "cache" ? "Clearing…" : "Clear cache"}
        </button>
        <button
          onClick={onExport}
          disabled={!!busy}
          className="rounded-xl border border-[var(--border)] px-3 py-2 text-xs font-medium transition hover:bg-[var(--background-secondary)] disabled:opacity-50"
        >
          {busy === "export" ? "Exporting…" : "Export offline data"}
        </button>
      </div>
    </div>
  );
}
