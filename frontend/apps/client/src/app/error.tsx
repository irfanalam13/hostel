"use client";

import { useEffect } from "react";
import { captureError } from "@hostel/utils";
import { ErrorState } from "@hostel/ui";

export default function RootError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    captureError(error, { boundary: "app/error", digest: error.digest });
  }, [error]);

  return <ErrorState error={error} onRetry={reset} />;
}
