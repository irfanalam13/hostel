"use client";

// Top-level safety net: catches errors thrown in the root layout itself.
// It must render its own <html>/<body> because it replaces the root layout.

import { useEffect } from "react";
import { captureError } from "@hostel/utils";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    captureError(error, { boundary: "global-error", digest: error.digest });
  }, [error]);

  return (
    <html lang="en">
      <body className="min-h-screen bg-zinc-50 text-zinc-900 antialiased">
        <div className="grid min-h-screen place-items-center px-4">
          <div className="w-full max-w-md rounded-2xl border border-zinc-200 bg-white p-6 text-center shadow-sm">
            <div className="mx-auto mb-4 grid h-12 w-12 place-items-center rounded-full bg-red-50 text-2xl">
              ⚠️
            </div>
            <h1 className="text-lg font-semibold">Application error</h1>
            <p className="mt-1 text-sm text-zinc-500">
              The app hit an unexpected error. Try again, or return to the dashboard.
            </p>
            <div className="mt-6 flex justify-center gap-3">
              <button
                type="button"
                onClick={reset}
                className="rounded-xl bg-zinc-900 px-4 py-2 text-sm font-medium text-white transition hover:opacity-90"
              >
                Retry
              </button>
              <button
                type="button"
                onClick={() => window.location.assign("/dashboard")}
                className="rounded-xl border border-zinc-200 bg-white px-4 py-2 text-sm font-medium text-zinc-800 transition hover:bg-zinc-50"
              >
                Go Home
              </button>
            </div>
          </div>
        </div>
      </body>
    </html>
  );
}
