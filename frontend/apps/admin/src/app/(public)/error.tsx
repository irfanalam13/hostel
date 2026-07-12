"use client";

import { useEffect } from "react";
import { captureError } from "@hostel/utils";
import { ErrorState } from "@hostel/ui";

export default function PublicError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    captureError(error, { boundary: "(public)/error", digest: error.digest });
  }, [error]);

  return (
    <ErrorState
      error={error}
      onRetry={reset}
      title="Something went wrong"
      description="We couldn't load this page. Please retry."
      onHome={() => window.location.assign("/login")}
    />
  );
}
