import { TESTIMONIALS, type Testimonial } from "./content";

/**
 * Dynamic testimonials + review system for the landing page.
 *
 * Reviews live in the backend (`apps.tenants.Testimonial`). The public endpoint
 * returns the admin-curated *featured* reviews plus aggregate rating stats
 * computed over all *approved* reviews. Anyone can submit a review; it lands
 * unapproved and only appears once an admin approves/features it.
 *
 * Like pricing, this is fetched server-side (SEO + ISR) with a graceful fallback
 * to the static copy so the section is never empty.
 */

export type TestimonialStats = {
  /** Number of approved reviews behind the stats. */
  total: number;
  /** Mean rating, 1 decimal (e.g. 4.6). */
  average_rating: number;
  /** Average as a percentage of 5 — "overall rating". */
  rating_percent: number;
  /** Share of reviews rated 4★+ — "appreciation". */
  appreciation_percent: number;
};

export type TestimonialsData = {
  items: Testimonial[];
  stats: TestimonialStats | null;
};

type PublicTestimonial = {
  id: number | string;
  author_name: string;
  author_role?: string;
  rating?: number;
  quote: string;
};

function apiBase(): string {
  return (process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api").replace(/\/+$/, "");
}

function unwrap<T>(json: unknown): T {
  // Tolerate the API's {success, data, meta} envelope or a raw body.
  if (json && typeof json === "object" && "data" in (json as Record<string, unknown>)) {
    return (json as { data: T }).data;
  }
  return json as T;
}

export async function getTestimonials(): Promise<TestimonialsData> {
  try {
    const res = await fetch(`${apiBase()}/tenants/testimonials/`, {
      next: { revalidate: 300 },
      // Hard-cap the wait: a cold/asleep backend (e.g. Render free tier) must
      // not hang the server render past the platform's function timeout — fail
      // fast and fall back to static copy instead of shipping a blank page.
      signal: AbortSignal.timeout(3500),
    });
    if (!res.ok) return { items: TESTIMONIALS, stats: null };

    const payload = unwrap<{ testimonials?: PublicTestimonial[]; stats?: TestimonialStats }>(
      await res.json(),
    );
    const list = payload?.testimonials ?? [];
    if (!Array.isArray(list) || list.length === 0) {
      // No curated reviews yet — keep the section populated with static copy,
      // but still surface real stats if any approved reviews exist.
      return { items: TESTIMONIALS, stats: payload?.stats ?? null };
    }

    const items: Testimonial[] = list.map((t) => ({
      name: t.author_name,
      role: t.author_role || "",
      quote: t.quote,
      rating: t.rating ?? 5,
    }));
    return { items, stats: payload?.stats ?? null };
  } catch {
    return { items: TESTIMONIALS, stats: null };
  }
}

export type ReviewInput = {
  author_name: string;
  author_role?: string;
  rating: number;
  quote: string;
};

export type SubmitResult = { ok: boolean; message: string };

/** Submit a review (client-side). Lands unapproved, pending admin moderation. */
export async function submitReview(input: ReviewInput): Promise<SubmitResult> {
  try {
    const res = await fetch(`${apiBase()}/tenants/testimonials/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    });
    const body = await res.json().catch(() => null);
    if (res.ok) {
      const data = unwrap<{ detail?: string }>(body);
      return { ok: true, message: data?.detail || "Thanks for your review!" };
    }
    if (res.status === 429) {
      return { ok: false, message: "You've submitted a few reviews already. Please try again later." };
    }
    const msg =
      (body && (body.message || body?.errors?.quote?.[0] || body?.errors?.rating?.[0])) ||
      "Couldn't submit your review. Please check your details and try again.";
    return { ok: false, message: String(msg) };
  } catch {
    return { ok: false, message: "Network error — please try again." };
  }
}
