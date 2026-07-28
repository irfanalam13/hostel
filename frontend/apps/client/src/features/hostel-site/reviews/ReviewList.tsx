"use client";

import { useState } from "react";
import { StarRating } from "@hostel/ui";
import { loadMoreReviews, type HostelReview } from "./api";

function ReviewCard({ review }: { review: HostelReview }) {
  return (
    <div className="site-card p-4">
      <div className="flex items-center justify-between gap-2">
        <StarRating value={review.rating} size="sm" color="var(--site-accent)" />
        <span className="text-xs text-gray-500">
          {new Date(review.created_at).toLocaleDateString(undefined, { year: "numeric", month: "short" })}
        </span>
      </div>
      <p className="mt-2 font-semibold text-gray-900">{review.title}</p>
      <p className="mt-1 whitespace-pre-line text-sm text-gray-700">{review.body}</p>
      <p className="mt-2 text-xs font-medium text-gray-500">{review.author_display_name}</p>
      {review.owner_response && (
        <div className="mt-3 rounded-lg bg-[var(--site-primary)]/5 p-3">
          <p className="text-xs font-semibold text-[var(--site-primary)]">Response from the hostel</p>
          <p className="mt-1 whitespace-pre-line text-sm text-gray-700">{review.owner_response.body}</p>
        </div>
      )}
    </div>
  );
}

export function ReviewList({ initial, initialNext }: { initial: HostelReview[]; initialNext: string | null }) {
  const [items, setItems] = useState(initial);
  const [next, setNext] = useState(initialNext);
  const [loading, setLoading] = useState(false);

  async function loadMore() {
    if (!next || loading) return;
    setLoading(true);
    try {
      const page = await loadMoreReviews(next);
      setItems((prev) => [...prev, ...page.items]);
      setNext(page.next);
    } finally {
      setLoading(false);
    }
  }

  if (items.length === 0) {
    return <p className="text-sm text-gray-500">No reviews yet — be the first to share your experience.</p>;
  }

  return (
    <div>
      <div className="grid gap-4 sm:grid-cols-2">
        {items.map((review) => (
          <ReviewCard key={review.id} review={review} />
        ))}
      </div>
      {next && (
        <div className="mt-6 flex justify-center">
          <button
            type="button"
            onClick={loadMore}
            disabled={loading}
            className="rounded-[var(--site-radius)] border border-gray-300 px-5 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-60"
          >
            {loading ? "Loading…" : "Load more reviews"}
          </button>
        </div>
      )}
    </div>
  );
}
