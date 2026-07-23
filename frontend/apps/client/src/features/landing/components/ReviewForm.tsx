"use client";

import React, { useState } from "react";
import { Star, CheckCircle2, Loader2 } from "lucide-react";
import { submitReview } from "../testimonials";

/**
 * Public "leave a review" form for the landing testimonials section. Submissions
 * are moderated server-side, so we tell the user it'll appear once approved.
 * Collapsed to a button until opened, to keep the section uncluttered.
 */
export function ReviewForm() {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [role, setRole] = useState("");
  const [rating, setRating] = useState(5);
  const [hover, setHover] = useState(0);
  const [quote, setQuote] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const result = await submitReview({
      author_name: name.trim(),
      author_role: role.trim(),
      rating,
      quote: quote.trim(),
    });
    setBusy(false);
    if (result.ok) {
      setDone(true);
    } else {
      setError(result.message);
    }
  };

  if (!open) {
    return (
      <div className="mt-12 text-center">
        <button
          onClick={() => setOpen(true)}
          className="inline-flex items-center gap-2 rounded-xl border border-[var(--border)] bg-[var(--card)] px-5 py-3 text-sm font-semibold text-[var(--foreground)] transition hover:border-[var(--accent)] hover:text-[var(--accent)]"
        >
          <Star className="h-4 w-4" aria-hidden />
          Leave a review
        </button>
      </div>
    );
  }

  if (done) {
    return (
      <div className="mx-auto mt-12 max-w-md rounded-2xl border border-[var(--border)] bg-[var(--card)] p-7 text-center shadow-[var(--shadow-sm)]">
        <CheckCircle2 className="mx-auto h-10 w-10 text-[var(--success)]" aria-hidden />
        <p className="mt-3 text-base font-semibold text-[var(--foreground)]">Thank you!</p>
        <p className="mt-1 text-sm text-[var(--muted)]">
          Your review was submitted and will appear once it&apos;s approved.
        </p>
      </div>
    );
  }

  return (
    <form
      onSubmit={onSubmit}
      className="mx-auto mt-12 max-w-lg rounded-2xl border border-[var(--border)] bg-[var(--card)] p-7 shadow-[var(--shadow-sm)]"
    >
      <h3 className="text-base font-semibold text-[var(--foreground)]">Share your experience</h3>

      {/* Star rating */}
      <div className="mt-4 flex items-center gap-1" role="radiogroup" aria-label="Rating">
        {[1, 2, 3, 4, 5].map((n) => {
          const active = (hover || rating) >= n;
          return (
            <button
              key={n}
              type="button"
              onClick={() => setRating(n)}
              onMouseEnter={() => setHover(n)}
              onMouseLeave={() => setHover(0)}
              role="radio"
              aria-checked={rating === n}
              aria-label={`${n} star${n === 1 ? "" : "s"}`}
              className="p-0.5"
            >
              <Star
                className={`h-7 w-7 transition ${
                  active ? "fill-[var(--warning)] text-[var(--warning)]" : "text-[var(--border-hover)]"
                }`}
                aria-hidden
              />
            </button>
          );
        })}
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <input
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Your name"
          maxLength={120}
          className="rounded-xl border border-[var(--border)] bg-[var(--card)] px-3.5 py-2.5 text-sm outline-none"
        />
        <input
          value={role}
          onChange={(e) => setRole(e.target.value)}
          placeholder="Role / hostel (optional)"
          maxLength={120}
          className="rounded-xl border border-[var(--border)] bg-[var(--card)] px-3.5 py-2.5 text-sm outline-none"
        />
      </div>

      <textarea
        required
        value={quote}
        onChange={(e) => setQuote(e.target.value)}
        placeholder="What do you love about the platform?"
        rows={4}
        minLength={10}
        maxLength={1000}
        className="mt-3 w-full resize-y rounded-xl border border-[var(--border)] bg-[var(--card)] px-3.5 py-2.5 text-sm outline-none"
      />

      {error && <p className="mt-3 text-sm text-[var(--error)]">{error}</p>}

      <div className="mt-4 flex items-center justify-end gap-2">
        <button
          type="button"
          onClick={() => setOpen(false)}
          className="rounded-xl border border-[var(--border)] px-4 py-2.5 text-sm font-medium text-[var(--foreground)] transition hover:bg-[var(--background-secondary)]"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={busy}
          className="inline-flex items-center gap-2 rounded-xl bg-[var(--accent)] px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-[var(--accent-hover)] disabled:opacity-60"
        >
          {busy && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}
          Submit review
        </button>
      </div>
    </form>
  );
}
