"use client";

import { useCallback, useEffect, useState } from "react";
import { authApi, type ActivityEvent } from "@/features/auth/api/auth.api";
import { Button } from "@hostel/ui";
import { Card } from "@hostel/ui";
import { Skeleton } from "@hostel/ui";
import { Activity, Globe, Monitor, RotateCw } from "lucide-react";
import { actionMeta, formatDateTime, parseUserAgent, relativeTime, toneColor } from "../lib";

export function ActivitySection() {
  const [events, setEvents] = useState<ActivityEvent[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setEvents(await authApi.activity(30));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't load your activity.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <Card>
      <div className="mb-1 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-base font-semibold text-[var(--foreground)]">
          <Activity className="h-4 w-4 text-[var(--accent)]" />
          Recent activity
        </div>
        <Button variant="ghost" size="sm" onClick={() => void load()} loading={loading} aria-label="Refresh">
          <RotateCw className="h-4 w-4" />
        </Button>
      </div>
      <p className="mb-4 text-sm text-[var(--muted)]">
        Sign-ins and account changes recorded for your user, newest first.
      </p>

      {loading && !events ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="flex items-center gap-3">
              <Skeleton className="h-9 w-9 rounded-full" />
              <div className="flex-1 space-y-2">
                <Skeleton className="h-3 w-40" />
                <Skeleton className="h-3 w-24" />
              </div>
            </div>
          ))}
        </div>
      ) : error ? (
        <div className="rounded-xl border border-dashed border-[var(--border)] bg-[var(--background-secondary)] px-4 py-8 text-center">
          <p className="text-sm text-[var(--muted)]">{error}</p>
          <Button variant="secondary" size="sm" className="mt-3" onClick={() => void load()}>
            Try again
          </Button>
        </div>
      ) : events && events.length > 0 ? (
        <ol className="relative space-y-1 border-l border-[var(--border)] pl-4">
          {events.map((e) => {
            const meta = actionMeta(e.action);
            const device = parseUserAgent(e.user_agent);
            return (
              <li key={e.id} className="relative py-2">
                <span
                  className="absolute -left-[22px] top-3.5 h-2.5 w-2.5 rounded-full ring-4 ring-[var(--card)]"
                  style={{ backgroundColor: toneColor(meta.tone) }}
                  aria-hidden
                />
                <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5">
                  <span className="text-sm font-medium text-[var(--foreground)]">
                    {e.message || meta.label}
                  </span>
                  <time
                    className="text-xs text-[var(--muted)]"
                    title={formatDateTime(e.created_at)}
                    dateTime={e.created_at}
                  >
                    {relativeTime(e.created_at)}
                  </time>
                </div>
                <div className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-[var(--muted)]">
                  <span
                    className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 font-medium"
                    style={{
                      color: toneColor(meta.tone),
                      backgroundColor: `color-mix(in srgb, ${toneColor(meta.tone)} 12%, transparent)`,
                    }}
                  >
                    {meta.label}
                  </span>
                  {device !== "Unknown device" && (
                    <span className="inline-flex items-center gap-1">
                      <Monitor className="h-3.5 w-3.5" />
                      {device}
                    </span>
                  )}
                  {e.ip_address && (
                    <span className="inline-flex items-center gap-1 font-mono">
                      <Globe className="h-3.5 w-3.5" />
                      {e.ip_address}
                    </span>
                  )}
                </div>
              </li>
            );
          })}
        </ol>
      ) : (
        <div className="rounded-xl border border-dashed border-[var(--border)] bg-[var(--background-secondary)] px-4 py-10 text-center">
          <div className="text-2xl" aria-hidden>
            🗒️
          </div>
          <p className="mt-2 text-sm font-medium text-[var(--foreground)]">No activity yet</p>
          <p className="text-sm text-[var(--muted)]">Sign-ins and account changes will show up here.</p>
        </div>
      )}
    </Card>
  );
}
