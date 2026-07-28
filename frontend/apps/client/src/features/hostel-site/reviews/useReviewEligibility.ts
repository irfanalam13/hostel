"use client";

import { useCallback, useEffect, useState } from "react";
import { getCurrentConsumer, getMyReview, type ConsumerUser, type MyReview } from "./reviewsApi";

export type EligibilityState =
  | { status: "checking" }
  | { status: "anonymous" }
  | { status: "no_review"; user: ConsumerUser }
  | { status: "has_review"; user: ConsumerUser; review: MyReview };

/**
 * Resolves the `WriteReviewCTA` state machine's session half: is there a
 * logged-in consumer, and have they already reviewed this hostel. Runs
 * client-side only (session cookie isn't readable server-side across the
 * cross-site deployment) — `discoveryFetch` carries the cookie via
 * `credentials: "include"`.
 */
export function useReviewEligibility(hostelSlug: string) {
  const [state, setState] = useState<EligibilityState>({ status: "checking" });

  const reload = useCallback(async () => {
    setState({ status: "checking" });
    const user = await getCurrentConsumer();
    if (!user) {
      setState({ status: "anonymous" });
      return;
    }
    const review = await getMyReview(hostelSlug);
    setState(review ? { status: "has_review", user, review } : { status: "no_review", user });
  }, [hostelSlug]);

  useEffect(() => {
    void reload();
  }, [reload]);

  return { state, reload };
}
