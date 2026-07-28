"use client";

import React, { useState } from "react";
import { StarRating } from "@hostel/ui";
import { DiscoveryApiError } from "@/features/discovery/discoveryFetch";
import { submitReview, updateReview, type MyReview } from "./reviewsApi";

const inputClass =
  "w-full rounded-[var(--site-radius)] border border-gray-300 bg-white px-3 py-2 text-sm " +
  "focus:outline-none focus:ring-2 focus:ring-[var(--site-primary)]";

/** Rating + text form, used both to submit a new review and to edit an
 * existing one. `hostelSlug` is only needed on create. */
export function ReviewForm({
  hostelSlug,
  existing,
  onSaved,
  onCancel,
}: {
  hostelSlug: string;
  existing?: MyReview;
  onSaved: () => void;
  onCancel?: () => void;
}) {
  const [rating, setRating] = useState(existing?.rating ?? 0);
  const [title, setTitle] = useState(existing?.title ?? "");
  const [body, setBody] = useState(existing?.body ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (rating < 1) {
      setError("Choose a star rating.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      if (existing) {
        await updateReview(existing.id, { rating, title, body });
      } else {
        await submitReview({ hostel: hostelSlug, rating, title, body });
      }
      onSaved();
    } catch (err) {
      setError(err instanceof DiscoveryApiError ? err.message : "Could not save your review. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="space-y-3" aria-label="Write a review">
      <div>
        <p className="mb-1 text-sm font-medium text-gray-700">Your rating</p>
        <StarRating value={rating} onChange={setRating} size="lg" color="var(--site-accent)" />
      </div>
      <input
        required
        placeholder="Give your review a title"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        className={inputClass}
        maxLength={150}
      />
      <textarea
        required
        placeholder="Share your experience living here…"
        value={body}
        onChange={(e) => setBody(e.target.value)}
        rows={5}
        className={inputClass}
        maxLength={4000}
      />
      {error && <p className="text-sm text-red-600">{error}</p>}
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={busy}
          className="rounded-[var(--site-radius)] bg-[var(--site-primary)] px-5 py-2.5 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-60"
        >
          {busy ? "Saving…" : existing ? "Save changes" : "Submit review"}
        </button>
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            className="rounded-[var(--site-radius)] border border-gray-300 px-5 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Cancel
          </button>
        )}
      </div>
    </form>
  );
}
