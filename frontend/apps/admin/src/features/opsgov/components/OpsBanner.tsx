"use client";

import React from "react";

import { fetchOpsStatus } from "../api/opsgov.api";
import type { OpsStatus } from "../types/opsgov.types";

const LEVEL_STYLES: Record<string, string> = {
  info: "bg-[color-mix(in_srgb,var(--info)_14%,transparent)] text-[var(--info)] border-[var(--info)]",
  warning: "bg-[color-mix(in_srgb,var(--warning)_16%,transparent)] text-[var(--warning)] border-[var(--warning)]",
  critical: "bg-[color-mix(in_srgb,var(--error)_16%,transparent)] text-[var(--error)] border-[var(--error)]",
};

const DISMISS_KEY = "opsbanner:dismissed";

function loadDismissed(): Set<string> {
  if (typeof window === "undefined") return new Set();
  try {
    return new Set(JSON.parse(localStorage.getItem(DISMISS_KEY) || "[]"));
  } catch {
    return new Set();
  }
}

/**
 * Global operational banner shown in every zone: active announcements,
 * in-progress/imminent maintenance, and open public incidents. Polls the
 * authenticated status feed; failures are silent (never blocks the app).
 */
export function OpsBanner() {
  const [status, setStatus] = React.useState<OpsStatus | null>(null);
  const [dismissed, setDismissed] = React.useState<Set<string>>(() => loadDismissed());

  React.useEffect(() => {
    let alive = true;
    const load = () =>
      fetchOpsStatus()
        .then((s) => alive && setStatus(s))
        .catch(() => {});
    load();
    const timer = setInterval(load, 60_000);
    return () => {
      alive = false;
      clearInterval(timer);
    };
  }, []);

  const dismiss = (id: string) => {
    const next = new Set(dismissed);
    next.add(id);
    setDismissed(next);
    try {
      localStorage.setItem(DISMISS_KEY, JSON.stringify([...next]));
    } catch {}
  };

  if (!status) return null;

  const announcements = status.announcements.filter((a) => !dismissed.has(a.id));
  const maintenance = status.maintenance.filter((m) => m.status === "in_progress");
  const incidents = status.incidents;

  if (!announcements.length && !maintenance.length && !incidents.length) return null;

  return (
    <div className="space-y-2 px-4 pt-3">
      {maintenance.map((m) => (
        <div
          key={m.id}
          className="flex items-center justify-between rounded-xl border border-[var(--warning)] bg-[color-mix(in_srgb,var(--warning)_16%,transparent)] px-4 py-2 text-sm text-[var(--warning)]"
        >
          <span>
            🛠️ Maintenance in progress: <strong>{m.title}</strong>
            {m.enforce_read_only ? " — the system is temporarily read-only." : ""}
          </span>
        </div>
      ))}

      {incidents.map((i) => (
        <div
          key={i.id}
          className="rounded-xl border border-[var(--error)] bg-[color-mix(in_srgb,var(--error)_14%,transparent)] px-4 py-2 text-sm text-[var(--error)]"
        >
          ⚠️ {i.severity.toUpperCase()} incident: <strong>{i.title}</strong> — {i.status}
        </div>
      ))}

      {announcements.map((a) => (
        <div
          key={a.id}
          className={`flex items-start justify-between gap-3 rounded-xl border px-4 py-2 text-sm ${
            LEVEL_STYLES[a.level] ?? LEVEL_STYLES.info
          }`}
        >
          <div>
            <strong>{a.title}</strong>
            {a.body ? <span className="opacity-90"> — {a.body}</span> : null}
          </div>
          {a.dismissible && (
            <button
              onClick={() => dismiss(a.id)}
              aria-label="Dismiss"
              className="shrink-0 opacity-70 hover:opacity-100"
            >
              ✕
            </button>
          )}
        </div>
      ))}
    </div>
  );
}
