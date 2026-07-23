"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Button, PageSkeleton } from "@hostel/ui";
import { workspacesApi } from "@/features/tenants/api/workspaces.api";
import type { Workspace } from "@/features/tenants/types/workspaces.types";

/**
 * Owner workspace selector (Phase 6).
 *
 * Lists the workspaces the signed-in user belongs to and lets an owner with
 * more than one hostel jump between them. Because JWT sessions are bound to a
 * single workspace (a token minted on one subdomain is a 401 on another),
 * selecting a *different* workspace does a full navigation to that workspace's
 * URL — where its own login/session takes over. The *current* workspace is an
 * in-app navigation to the dashboard.
 *
 * The login flow itself stays deterministic (a workspace host, or a Hostel ID
 * on the root domain, already resolves exactly one workspace); this page is the
 * additive "I own several hostels — take me to another one" affordance, and it
 * auto-forwards when there is only one.
 */
export default function SelectWorkspacePage() {
  const router = useRouter();
  const [workspaces, setWorkspaces] = useState<Workspace[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    workspacesApi
      .list()
      .then((res) => {
        if (cancelled) return;
        const list = Array.isArray(res) ? res : res?.results ?? [];
        // Exactly one workspace → nothing to choose; go straight in.
        if (list.length === 1) {
          go(list[0]);
          return;
        }
        setWorkspaces(list);
      })
      .catch((e: unknown) => {
        if (!cancelled) setError((e as { message?: string })?.message || "Could not load your workspaces.");
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function go(ws: Workspace) {
    // Same host as the one we're on → internal nav (keeps the current session).
    // Different host → full navigation; the target workspace signs the user in.
    try {
      const target = new URL(ws.workspace_url);
      if (typeof window !== "undefined" && target.host === window.location.host) {
        router.replace("/dashboard");
        return;
      }
      if (typeof window !== "undefined") {
        window.location.assign(`${ws.workspace_url.replace(/\/$/, "")}/dashboard`);
        return;
      }
    } catch {
      // Malformed URL — fall back to internal dashboard.
    }
    router.replace("/dashboard");
  }

  if (error) {
    return (
      <div className="mx-auto max-w-md p-6">
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
        <Button className="mt-4 w-full" onClick={() => router.replace("/dashboard")}>
          Go to dashboard
        </Button>
      </div>
    );
  }

  if (!workspaces) {
    return (
      <div className="mx-auto max-w-2xl p-6">
        <PageSkeleton />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl p-6">
      <h1 className="text-2xl font-bold text-[var(--foreground)]">Choose a workspace</h1>
      <p className="mt-1 text-[var(--muted-foreground,#6b7280)]">
        You belong to {workspaces.length} workspaces. Pick the one you want to open.
      </p>

      <ul className="mt-6 space-y-3">
        {workspaces.map((ws) => (
          <li key={ws.id}>
            <button
              onClick={() => go(ws)}
              className="flex w-full items-center gap-4 rounded-2xl border border-[var(--border,#e5e7eb)] bg-[var(--card,#fff)] p-4 text-left transition hover:border-blue-400 hover:shadow-sm"
            >
              {ws.logo ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={ws.logo} alt="" className="h-12 w-12 rounded-xl object-contain" />
              ) : (
                <div className="grid h-12 w-12 place-items-center rounded-xl bg-blue-50 text-2xl">🏨</div>
              )}
              <div className="min-w-0 flex-1">
                <div className="truncate font-semibold text-[var(--foreground)]">{ws.name}</div>
                <div className="truncate font-mono text-xs text-[var(--muted-foreground,#6b7280)]">
                  {ws.slug} · {ws.status}
                </div>
              </div>
              <span aria-hidden className="text-[var(--muted-foreground,#9ca3af)]">→</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
