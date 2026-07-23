"use client";

import React from "react";

/**
 * User-friendly error screen with Retry + Go Home actions. Shared by the
 * route-level `error.tsx` boundaries and the component-level `ErrorBoundary`.
 * Raw error details are only shown in development.
 */
export function ErrorState({
  title = "Something went wrong",
  description = "An unexpected error occurred. You can retry, or head back to the dashboard.",
  error,
  onRetry,
  onHome,
  compact = false,
}: {
  title?: string;
  description?: string;
  error?: unknown;
  onRetry?: () => void;
  onHome?: () => void;
  compact?: boolean;
}) {
  const isDev = typeof process !== "undefined" && process.env.NODE_ENV !== "production";
  const detail =
    isDev && error
      ? error instanceof Error
        ? error.message
        : String(error)
      : "";

  function goHome() {
    if (onHome) return onHome();
    if (typeof window !== "undefined") window.location.assign("/dashboard");
  }

  return (
    <div
      className={`grid place-items-center ${compact ? "py-10" : "min-h-[60vh]"} px-4`}
      role="alert"
    >
      <div className="w-full max-w-md rounded-2xl border border-zinc-200 bg-white p-6 text-center shadow-sm">
        <div className="mx-auto mb-4 grid h-12 w-12 place-items-center rounded-full bg-red-50 text-2xl">
          ⚠️
        </div>
        <h2 className="text-lg font-semibold text-zinc-900">{title}</h2>
        <p className="mt-1 text-sm text-zinc-500">{description}</p>

        {detail ? (
          <pre className="mt-4 max-h-32 overflow-auto rounded-lg bg-zinc-50 p-3 text-left text-xs text-zinc-600">
            {detail}
          </pre>
        ) : null}

        <div className="mt-6 flex justify-center gap-3">
          {onRetry ? (
            <button
              type="button"
              onClick={onRetry}
              className="rounded-xl bg-zinc-900 px-4 py-2 text-sm font-medium text-white transition hover:opacity-90 active:scale-[0.98]"
            >
              Retry
            </button>
          ) : null}
          <button
            type="button"
            onClick={goHome}
            className="rounded-xl border border-zinc-200 bg-white px-4 py-2 text-sm font-medium text-zinc-800 transition hover:bg-zinc-50 active:scale-[0.98]"
          >
            Go Home
          </button>
        </div>
      </div>
    </div>
  );
}
