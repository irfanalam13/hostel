"use client";

import { useEffect, useState } from "react";

/**
 * Offline fallback page. The service worker precaches this route and serves it
 * for navigations that fail while offline (see public/sw.js handleNavigation).
 * It is intentionally self-contained and depends on no authenticated data so it
 * always renders without a network connection.
 */
export default function OfflinePage() {
  const [online, setOnline] = useState(true);

  useEffect(() => {
    setOnline(navigator.onLine);
    const on = () => setOnline(true);
    const off = () => setOnline(false);
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    return () => {
      window.removeEventListener("online", on);
      window.removeEventListener("offline", off);
    };
  }, []);

  // When the connection returns, take the user back to where they came from.
  useEffect(() => {
    if (online) window.location.reload();
  }, [online]);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 bg-[var(--background)] px-6 text-center text-[var(--foreground)]">
      <div className="flex h-20 w-20 items-center justify-center rounded-3xl bg-[var(--accent)] text-white shadow-lg">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
          <path d="M1 1l22 22" strokeLinecap="round" />
          <path d="M16.72 11.06A10.94 10.94 0 0 1 19 12.55" strokeLinecap="round" />
          <path d="M5 12.55a10.94 10.94 0 0 1 5.17-2.39" strokeLinecap="round" />
          <path d="M10.71 5.05A16 16 0 0 1 22.58 9" strokeLinecap="round" />
          <path d="M1.42 9a15.91 15.91 0 0 1 4.7-2.88" strokeLinecap="round" />
          <path d="M8.53 16.11a6 6 0 0 1 6.95 0" strokeLinecap="round" />
          <line x1="12" y1="20" x2="12.01" y2="20" strokeLinecap="round" />
        </svg>
      </div>

      <div className="space-y-2">
        <h1 className="text-2xl font-semibold">You&apos;re offline</h1>
        <p className="max-w-sm text-[var(--muted)]">
          {online
            ? "Reconnecting…"
            : "This page isn't available offline. Pages you've already visited will still work. We'll reconnect automatically when you're back online."}
        </p>
      </div>

      <div className="flex gap-3">
        <button
          onClick={() => window.location.reload()}
          className="rounded-xl bg-[var(--accent)] px-5 py-2.5 font-medium text-white transition hover:bg-[var(--accent-hover)]"
        >
          Try again
        </button>
        <button
          onClick={() => (window.location.href = "/dashboard")}
          className="rounded-xl border border-[var(--border)] px-5 py-2.5 font-medium transition hover:bg-[var(--background-secondary)]"
        >
          Go to dashboard
        </button>
      </div>

      <span
        className={`mt-2 inline-flex items-center gap-2 rounded-full px-3 py-1 text-sm ${
          online ? "bg-[var(--success)]/10 text-[var(--success)]" : "bg-[var(--muted)]/10 text-[var(--muted)]"
        }`}
      >
        <span className={`h-2 w-2 rounded-full ${online ? "bg-[var(--success)]" : "bg-[var(--muted)]"}`} />
        {online ? "Online" : "No connection"}
      </span>
    </main>
  );
}
