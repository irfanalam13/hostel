"use client";

import React, { useState } from "react";
import { StarRating } from "@hostel/ui";
import { useReviewEligibility } from "./useReviewEligibility";
import { ConsumerAuthForm } from "./ConsumerAuthForm";
import { ReviewForm } from "./ReviewForm";
import { deleteReview } from "./reviewsApi";

const STATUS_COPY: Record<string, { title: string; body: string }> = {
  pending: {
    title: "Submitted — pending confirmation",
    body: "We couldn't automatically confirm your stay. The hostel will review and publish it shortly.",
  },
  rejected: {
    title: "Not published",
    body: "The hostel wasn't able to confirm this review. You can edit and resubmit the details.",
  },
  flagged: {
    title: "Under review",
    body: "This review was reported and is being looked at by our team.",
  },
  removed: {
    title: "Removed",
    body: "This review was removed following a report.",
  },
};

/**
 * Drives its own state machine for writing a review from a hostel's public
 * page — never a dead end for an anonymous or ineligible visitor. See the
 * table in the discovery/reviews plan: anonymous -> inline signup/login,
 * checking -> spinner, verified/no review yet -> the review form, pending ->
 * an explanatory message (not silently hidden), already reviewed -> the
 * existing review with edit/delete.
 */
export function WriteReviewCTA({ hostelSlug }: { hostelSlug: string }) {
  const { state, reload } = useReviewEligibility(hostelSlug);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(false);
  const [busy, setBusy] = useState(false);

  if (state.status === "checking") {
    return (
      <div className="flex items-center gap-2 text-sm text-gray-500">
        <span className="h-4 w-4 animate-spin rounded-full border-2 border-gray-300 border-t-[var(--site-primary)]" />
        Checking your review status…
      </div>
    );
  }

  const writeButtonClass =
    "rounded-[var(--site-radius)] bg-[var(--site-primary)] px-5 py-2.5 text-sm font-semibold text-white hover:opacity-90";

  if (state.status === "anonymous") {
    if (!open) {
      return (
        <button type="button" onClick={() => setOpen(true)} className={writeButtonClass}>
          Write a review
        </button>
      );
    }
    return <ConsumerAuthForm onDone={() => { setOpen(false); void reload(); }} />;
  }

  if (state.status === "no_review") {
    if (!open) {
      return (
        <button type="button" onClick={() => setOpen(true)} className={writeButtonClass}>
          Write a review
        </button>
      );
    }
    return <ReviewForm hostelSlug={hostelSlug} onSaved={() => { setOpen(false); void reload(); }} onCancel={() => setOpen(false)} />;
  }

  // state.status === "has_review"
  const { review } = state;

  if (editing) {
    return (
      <ReviewForm
        hostelSlug={hostelSlug}
        existing={review}
        onSaved={() => { setEditing(false); void reload(); }}
        onCancel={() => setEditing(false)}
      />
    );
  }

  async function onDelete() {
    if (!window.confirm("Delete your review? This can't be undone.")) return;
    setBusy(true);
    try {
      await deleteReview(review.id);
      await reload();
    } finally {
      setBusy(false);
    }
  }

  const notice = review.status !== "published" ? STATUS_COPY[review.status] : null;

  return (
    <div className="rounded-2xl border border-gray-200 p-5">
      {notice && (
        <div className="mb-3 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800">
          <p className="font-medium">{notice.title}</p>
          <p>{notice.body}</p>
        </div>
      )}
      <StarRating value={review.rating} size="sm" color="var(--site-accent)" />
      <p className="mt-1 font-semibold text-gray-900">{review.title}</p>
      <p className="mt-1 whitespace-pre-line text-sm text-gray-700">{review.body}</p>
      <div className="mt-3 flex gap-2">
        <button
          type="button"
          onClick={() => setEditing(true)}
          className="text-sm font-medium text-[var(--site-primary)] hover:underline"
        >
          Edit
        </button>
        <button
          type="button"
          onClick={onDelete}
          disabled={busy}
          className="text-sm font-medium text-red-600 hover:underline disabled:opacity-60"
        >
          Delete
        </button>
      </div>
    </div>
  );
}
