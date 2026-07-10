"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useToast } from "@hostel/ui";
import { captureMessage } from "@hostel/utils";

type UseApiOptions<T> = {
  /** Run automatically on mount (default true). */
  immediate?: boolean;
  /** Re-run when any of these values change. */
  deps?: unknown[];
  /** Show a toast when the fetch fails (default true). */
  toastOnError?: boolean;
  onSuccess?: (data: T) => void;
  onError?: (error: unknown) => void;
};

type UseApiResult<T> = {
  data: T | null;
  loading: boolean;
  error: string | null;
  /** Manually (re)run the fetch. Safe to call repeatedly — overlapping calls
   *  are ignored while one is in flight. */
  refetch: () => Promise<void>;
  setData: React.Dispatch<React.SetStateAction<T | null>>;
};

function messageOf(error: unknown): string {
  if (error instanceof Error) return error.message;
  if (typeof error === "string") return error;
  return "Request failed";
}

/**
 * Declarative data fetching with built-in loading/error state, a de-duplicated
 * refetch, and automatic error toasts. Eliminates the copy-pasted
 * try/catch/setLoading blocks scattered across pages.
 */
export function useApi<T>(
  fetcher: () => Promise<T>,
  options: UseApiOptions<T> = {}
): UseApiResult<T> {
  const { immediate = true, deps = [] } = options;
  const toast = useToast();

  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState<boolean>(immediate);
  const [error, setError] = useState<string | null>(null);

  // Keep latest callbacks/fetcher without forcing refetch identity churn.
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;
  const optsRef = useRef(options);
  optsRef.current = options;
  const inFlight = useRef(false);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  const refetch = useCallback(async () => {
    // Prevent duplicate/overlapping requests (e.g. double clicks on Refresh).
    if (inFlight.current) return;
    inFlight.current = true;
    setLoading(true);
    setError(null);
    try {
      const result = await fetcherRef.current();
      if (!mounted.current) return;
      setData(result);
      optsRef.current.onSuccess?.(result);
    } catch (err) {
      if (!mounted.current) return;
      const msg = messageOf(err);
      setError(msg);
      captureMessage(`useApi fetch failed: ${msg}`);
      if (optsRef.current.toastOnError ?? true) {
        toast.error(msg);
      }
      optsRef.current.onError?.(err);
    } finally {
      inFlight.current = false;
      if (mounted.current) setLoading(false);
    }
    // toastOnError is read from optsRef; toast is stable from context.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [toast]);

  useEffect(() => {
    if (immediate) void refetch();
    // `deps` is a caller-provided dependency list; refetch/immediate are stable.
  }, deps);

  return { data, loading, error, refetch, setData };
}
