/**
 * Server-side fetch of the public, cross-hostel discovery directory.
 *
 * Raw `fetch` (not `@hostel/api`'s `apiFetch`) so the pagination cursors in
 * `meta.pagination` survive — `apiFetch` unwraps the envelope and discards
 * `meta`, which is fine for the small tenant-scoped lists it's normally used
 * for, but wrong for a paginated, cacheable, anonymous directory. Same
 * pattern as `hostel-site/api.ts`'s `getPublicWebsite`.
 */

export type DirectoryHostel = {
  workspace: string;
  name: string;
  city: string;
  district: string;
  hostel_type: string;
  cover_image: string;
  average_rating: number;
  rating_count: number;
  amenity_tags: string[];
  public_url: string;
};

export type DirectoryQuery = {
  city?: string;
  district?: string;
  hostel_type?: string;
  min_rating?: number;
  amenity?: string;
  search?: string;
  ordering?: string;
  page?: number;
};

export type DirectoryPage = {
  items: DirectoryHostel[];
  count: number;
  next: string | null;
  previous: string | null;
};

function apiBase(): string {
  return (
    process.env.API_INTERNAL_URL ||
    process.env.NEXT_PUBLIC_API_BASE_URL ||
    "http://localhost:8000/api"
  ).replace(/\/+$/, "");
}

function buildQuery(query: DirectoryQuery): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== null && value !== "") params.set(key, String(value));
  }
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

async function parsePage(res: Response): Promise<DirectoryPage> {
  const body = (await res.json()) as {
    data?: DirectoryHostel[];
    meta?: { pagination?: { count?: number; next?: string | null; previous?: string | null } };
  };
  return {
    items: Array.isArray(body.data) ? body.data : [],
    count: body.meta?.pagination?.count ?? 0,
    next: body.meta?.pagination?.next ?? null,
    previous: body.meta?.pagination?.previous ?? null,
  };
}

export async function listDirectoryHostels(query: DirectoryQuery = {}): Promise<DirectoryPage> {
  try {
    const res = await fetch(`${apiBase()}/discovery/hostels/${buildQuery(query)}`, {
      next: { revalidate: 60 },
      signal: AbortSignal.timeout(5000),
    });
    if (!res.ok) return { items: [], count: 0, next: null, previous: null };
    return await parsePage(res);
  } catch {
    return { items: [], count: 0, next: null, previous: null };
  }
}

/**
 * Client-side "load more". DRF builds `next`/`previous` as absolute URLs from
 * whatever host the SSR request hit — in split deployments that's an
 * internal-only address, unreachable from the browser. Strip it down to
 * path+query and refetch against the public, browser-facing API base.
 */
export async function loadMoreDirectoryHostels(nextUrl: string): Promise<DirectoryPage> {
  let pathAndQuery = nextUrl;
  try {
    const parsed = new URL(nextUrl);
    pathAndQuery = `${parsed.pathname}${parsed.search}`;
  } catch {
    // Already relative — use as-is.
  }
  const publicBase = (process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api").replace(/\/+$/, "");
  const origin = publicBase.replace(/\/api$/, "");
  const res = await fetch(`${origin}${pathAndQuery}`, { cache: "no-store" });
  if (!res.ok) return { items: [], count: 0, next: null, previous: null };
  return await parsePage(res);
}
