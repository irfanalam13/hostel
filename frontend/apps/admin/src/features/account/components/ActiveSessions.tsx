"use client";

import { useCallback, useEffect, useState } from "react";
import { authApi, type SessionInfo } from "@/features/auth/api/auth.api";
import { Button } from "@hostel/ui";
import { Card } from "@hostel/ui";
import { Skeleton } from "@hostel/ui";
import { useConfirm } from "@hostel/ui";
import { useToast } from "@hostel/ui";
import { Laptop, MonitorSmartphone } from "lucide-react";
import { formatDateTime, relativeTime } from "../lib";

export function ActiveSessions() {
  const confirm = useConfirm();
  const toast = useToast();
  const [sessions, setSessions] = useState<SessionInfo[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [revoking, setRevoking] = useState<number | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setSessions(await authApi.sessions());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't load your sessions.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function revoke(session: SessionInfo) {
    const ok = await confirm({
      title: "Sign this device out?",
      message: "This session will be signed out immediately and will need to log in again.",
      confirmText: "Sign out device",
      danger: true,
    });
    if (!ok) return;
    setRevoking(session.id);
    try {
      await authApi.revokeSession(session.id);
      toast.success("That device has been signed out.");
      await load();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Couldn't sign that device out.");
    } finally {
      setRevoking(null);
    }
  }

  return (
    <Card>
      <div className="mb-1 flex items-center gap-2 text-base font-semibold text-[var(--foreground)]">
        <MonitorSmartphone className="h-4 w-4 text-[var(--accent)]" />
        Active sessions
      </div>
      <p className="mb-4 text-sm text-[var(--muted)]">
        Devices with a live sign-in for your account. Sign out any you don&apos;t recognise.
      </p>

      {loading && !sessions ? (
        <div className="space-y-3">
          {Array.from({ length: 2 }).map((_, i) => (
            <div key={i} className="flex items-center gap-3 rounded-xl border border-[var(--border)] p-3">
              <Skeleton className="h-10 w-10 rounded-lg" />
              <div className="flex-1 space-y-2">
                <Skeleton className="h-3 w-32" />
                <Skeleton className="h-3 w-48" />
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
      ) : (
        <ul className="space-y-2">
          {(sessions || []).map((s) => (
            <li
              key={s.id}
              className="flex items-center gap-3 rounded-xl border border-[var(--border)] bg-[var(--background-secondary)] p-3"
            >
              <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-[var(--card)] text-[var(--muted)]">
                <Laptop className="h-5 w-5" />
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="truncate text-sm font-medium text-[var(--foreground)]">
                    {s.current ? s.device || "This device" : "Signed-in device"}
                  </span>
                  {s.current && (
                    <span className="rounded-full bg-[var(--success)]/15 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-[var(--success)]">
                      This device
                    </span>
                  )}
                </div>
                <div className="mt-0.5 text-xs text-[var(--muted)]">
                  Signed in {relativeTime(s.created_at)} · expires {formatDateTime(s.expires_at)}
                </div>
              </div>
              {!s.current && (
                <Button
                  variant="secondary"
                  size="sm"
                  loading={revoking === s.id}
                  onClick={() => void revoke(s)}
                  className="shrink-0"
                >
                  Sign out
                </Button>
              )}
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
