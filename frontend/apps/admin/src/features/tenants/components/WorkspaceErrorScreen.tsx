"use client";

import React from "react";

type Props = {
  /** Machine code from the tenant middleware (err.code via isWorkspaceError). */
  code: string;
  /** Workspace label from the URL, when known — shown for context. */
  workspace?: string | null;
};

const COPY: Record<string, { title: string; body: string }> = {
  workspace_not_found: {
    title: "Workspace not found",
    body: "There is no hostel workspace at this address. Check the web address, or contact your hostel for the correct link.",
  },
  workspace_suspended: {
    title: "Workspace suspended",
    body: "This workspace is currently suspended. If you are the owner, please contact support to restore access.",
  },
  workspace_expired: {
    title: "Subscription expired",
    body: "This workspace's subscription has expired. If you are the owner, renew the subscription to restore access.",
  },
  workspace_pending: {
    title: "Workspace not ready",
    body: "This workspace is still being set up. Please try again shortly.",
  },
  workspace_inactive: {
    title: "Workspace disabled",
    body: "This workspace has been disabled. If you believe this is a mistake, contact support.",
  },
};

/**
 * Professional full-page error state for workspace-level failures
 * (not found / suspended / expired / disabled) shown instead of a login page.
 */
export function WorkspaceErrorScreen({ code, workspace }: Props) {
  const copy = COPY[code] || COPY.workspace_not_found;
  return (
    <main className="min-h-screen grid place-items-center p-6 bg-gray-50">
      <div className="max-w-md w-full bg-white border rounded-2xl p-8 shadow-sm text-center">
        <div className="text-5xl">🏢</div>
        <h1 className="mt-3 text-xl font-bold text-gray-900">{copy.title}</h1>
        {workspace ? (
          <div className="mt-1 text-sm font-mono text-gray-500">{workspace}</div>
        ) : null}
        <p className="mt-3 text-sm text-gray-600">{copy.body}</p>
        <a
          href="/"
          className="mt-6 inline-block rounded-xl bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:opacity-90"
        >
          Go to homepage
        </a>
      </div>
    </main>
  );
}
