"use client";

import { useEffect, useRef } from "react";
import { onBackgroundTask, type BackgroundTaskId } from "./backgroundTasks";

/**
 * Re-run `callback` whenever the named background task ticks (foreground timer)
 * or the service worker reports a background refresh for it. Components use this
 * to keep their data fresh without owning a timer:
 *
 *   useBackgroundRefresh("refresh-notifications", loadNotifs);
 *
 * The callback is held in a ref, so passing an inline function is fine — the
 * subscription is set up once and always calls the latest callback.
 */
export function useBackgroundRefresh(
  id: BackgroundTaskId,
  callback: () => void,
  options: { enabled?: boolean } = {},
): void {
  const { enabled = true } = options;
  const cbRef = useRef(callback);
  // Keep the ref pointing at the latest callback. Done in an effect (not during
  // render) so we never mutate a ref while rendering; the subscription below only
  // reads cbRef.current from async background-task events, which fire post-commit.
  useEffect(() => {
    cbRef.current = callback;
  });

  useEffect(() => {
    if (!enabled) return;
    return onBackgroundTask(id, () => cbRef.current());
  }, [id, enabled]);
}
