"use client";

import { useEffect } from "react";
import { captureError } from "@/shared/lib/monitoring";
import { ErrorState } from "@/shared/ui/ErrorState";

export default function ProtectedError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    captureError(error, { boundary: "(protected)/error", digest: error.digest });
  }, [error]);

  return (
    <ErrorState
      error={error}
      onRetry={reset}
      title="This page failed to load"
      description="Something went wrong while loading this section. Retry, or go back to the dashboard."
    />
  );
}
