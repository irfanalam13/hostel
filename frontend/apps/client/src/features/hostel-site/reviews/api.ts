/**
 * Server-side fetch of a hostel's public rating summary + published reviews,
 * for the `ReviewsSection` rendered inside `HostelSite`.
 *
 * Same internal-vs-public API base handling as `hostel-site/api.ts`'s
 * `getPublicWebsite` (Docker service networking on the server differs from
 * the browser-facing URL). Two round trips (hostel detail for the rating
 * summary, reviews list for the review cards) because
 * `/api/discovery/hostels/{slug}/reviews/` only returns the reviews
 * themselves — the rating aggregate lives on the hostel detail endpoint.
 */

export type HostelReview = {
  id: string;
  rating: number;
  title: string;
  body: string;
  resident_name_snapshot?: string;
  author_display_name: string;
  verification_method: string;
  stay_start: string | null;
  stay_end: string | null;
  owner_response: { body: string; created_at: string } | null;
  created_at: string;
};

export type RatingSummary = {
  average: number;
  count: number;
  breakdown: Record<string, number>;
};

export type ReviewsSectionData = {
  rating: RatingSummary;
  reviews: HostelReview[];
  next: string | null;
};

function apiBase(): string {
  return (
    process.env.API_INTERNAL_URL ||
    process.env.NEXT_PUBLIC_API_BASE_URL ||
    "http://localhost:8000/api"
  ).replace(/\/+$/, "");
}

const EMPTY: ReviewsSectionData = { rating: { average: 0, count: 0, breakdown: {} }, reviews: [], next: null };

/** Client-side "load more" for the review list — same absolute-URL-from-DRF
 * caveat as `directory/api.ts`'s `loadMoreDirectoryHostels`: strip to
 * path+query and refetch against the public API base. */
export async function loadMoreReviews(nextUrl: string): Promise<{ items: HostelReview[]; next: string | null }> {
  let pathAndQuery = nextUrl;
  try {
    const parsed = new URL(nextUrl);
    pathAndQuery = `${parsed.pathname}${parsed.search}`;
  } catch {
    // Already relative — use as-is.
  }
  const publicBase = (process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api").replace(/\/+$/, "");
  const origin = publicBase.replace(/\/api$/, "");
  try {
    const res = await fetch(`${origin}${pathAndQuery}`, { cache: "no-store" });
    if (!res.ok) return { items: [], next: null };
    const body = (await res.json()) as { data?: HostelReview[]; meta?: { pagination?: { next?: string | null } } };
    return { items: Array.isArray(body.data) ? body.data : [], next: body.meta?.pagination?.next ?? null };
  } catch {
    return { items: [], next: null };
  }
}

export async function getReviewsSectionData(slug: string): Promise<ReviewsSectionData> {
  if (!slug) return EMPTY;
  try {
    const [detailRes, reviewsRes] = await Promise.all([
      fetch(`${apiBase()}/discovery/hostels/${slug}/`, {
        next: { revalidate: 60 },
        signal: AbortSignal.timeout(5000),
      }),
      fetch(`${apiBase()}/discovery/hostels/${slug}/reviews/`, {
        next: { revalidate: 60 },
        signal: AbortSignal.timeout(5000),
      }),
    ]);

    let rating = EMPTY.rating;
    if (detailRes.ok) {
      const body = (await detailRes.json()) as {
        data?: { average_rating?: number; rating_count?: number; rating_breakdown?: Record<string, number> };
      };
      rating = {
        average: body.data?.average_rating ?? 0,
        count: body.data?.rating_count ?? 0,
        breakdown: body.data?.rating_breakdown ?? {},
      };
    }

    let reviews: HostelReview[] = [];
    let next: string | null = null;
    if (reviewsRes.ok) {
      const body = (await reviewsRes.json()) as {
        data?: HostelReview[];
        meta?: { pagination?: { next?: string | null } };
      };
      reviews = Array.isArray(body.data) ? body.data : [];
      next = body.meta?.pagination?.next ?? null;
    }

    return { rating, reviews, next };
  } catch {
    return EMPTY;
  }
}
