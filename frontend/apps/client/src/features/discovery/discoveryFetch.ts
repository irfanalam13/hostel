"use client";

/**
 * Fetch wrapper for the discovery/consumer-auth surface (signup, login,
 * review CRUD, "my review" lookups).
 *
 * Deliberately does NOT use `@hostel/api`'s `apiFetch`/`useAuth()`: those
 * always forward an `X-Workspace` header derived from the current hostname
 * (see `packages/api/src/apiClient.ts` `buildHeaders()`). A consumer
 * (reviewer) session is bound to the hidden platform workspace, not to
 * whichever hostel's subdomain the review UI happens to be rendered on — if
 * this ran through `apiFetch` while embedded on `everest.<domain>`, the
 * backend's cross-tenant token check would reject every request with
 * "This session belongs to a different workspace" (`CookieJWTAuthentication`
 * in `backend/apps/accounts/authentication.py`). This wrapper reuses the same
 * cookie/CSRF/refresh mechanics, just without ever attaching a workspace
 * header.
 */

const API_BASE = (
  process.env.NEXT_PUBLIC_API_BASE_URL?.trim() || "http://localhost:8000/api"
).replace(/\/+$/, "");

function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp("(?:^|;\\s*)" + name + "=([^;]+)"));
  return match ? decodeURIComponent(match[1]) : null;
}

let csrfToken: string | null = null;

async function ensureCsrf(force = false): Promise<string | null> {
  if (!force) {
    if (csrfToken) return csrfToken;
    const fromCookie = readCookie("csrftoken");
    if (fromCookie) {
      csrfToken = fromCookie;
      return csrfToken;
    }
  }
  try {
    const res = await fetch(`${API_BASE}/auth/csrf/`, { credentials: "include", cache: "no-store" });
    const body = (await res.json().catch(() => null)) as { csrftoken?: string } | null;
    csrfToken = body?.csrftoken || readCookie("csrftoken") || null;
  } catch {
    csrfToken = readCookie("csrftoken");
  }
  return csrfToken;
}

const SAFE_METHODS = ["GET", "HEAD", "OPTIONS"];

export class DiscoveryApiError extends Error {
  status: number;
  fieldErrors?: unknown;
  code?: string;

  constructor(message: string, status: number, fieldErrors?: unknown, code?: string) {
    super(message);
    this.name = "DiscoveryApiError";
    this.status = status;
    this.fieldErrors = fieldErrors;
    this.code = code;
  }
}

type Envelope<T> = { success: boolean; message?: string; data: T; meta?: { code?: string }; errors?: unknown };

function isEnvelope(body: unknown): body is Envelope<unknown> {
  return !!body && typeof body === "object" && "success" in body && "data" in body;
}

function apiUrl(path: string): string {
  if (path.startsWith("http")) return path;
  return `${API_BASE}${path.startsWith("/") ? path : `/${path}`}`;
}

export type DiscoveryFetchOptions = Omit<RequestInit, "body"> & {
  body?: unknown;
  /** Set false to skip the single silent-refresh-and-retry on a 401. */
  retryOn401?: boolean;
};

export async function discoveryFetch<T = unknown>(
  path: string,
  options: DiscoveryFetchOptions = {},
): Promise<T> {
  const method = (options.method || "GET").toUpperCase();
  const url = apiUrl(path);
  const isJsonBody = options.body !== undefined && !(options.body instanceof FormData);

  const buildHeaders = () => {
    const headers = new Headers(options.headers || {});
    if (isJsonBody && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
    if (!SAFE_METHODS.includes(method) && csrfToken) headers.set("X-CSRFToken", csrfToken);
    return headers;
  };

  const body = isJsonBody ? JSON.stringify(options.body) : (options.body as BodyInit | undefined);

  if (!SAFE_METHODS.includes(method)) await ensureCsrf();

  let res = await fetch(url, { ...options, method, body, headers: buildHeaders(), credentials: "include", cache: "no-store" });

  if (res.status === 403 && !SAFE_METHODS.includes(method)) {
    await ensureCsrf(true);
    res = await fetch(url, { ...options, method, body, headers: buildHeaders(), credentials: "include", cache: "no-store" });
  }

  if (res.status === 401 && options.retryOn401 !== false) {
    const refreshed = await fetch(`${API_BASE}/auth/token/refresh/`, {
      method: "POST",
      credentials: "include",
      cache: "no-store",
    });
    if (refreshed.ok) {
      res = await fetch(url, { ...options, method, body, headers: buildHeaders(), credentials: "include", cache: "no-store" });
    }
  }

  if (res.status === 204) return undefined as T;

  const contentType = res.headers.get("content-type") || "";
  const parsed = contentType.includes("application/json") ? await res.json().catch(() => null) : null;

  if (!res.ok) {
    const env = isEnvelope(parsed) ? parsed : null;
    const message = env?.message || "Something went wrong. Please try again.";
    const code = env?.meta?.code;
    throw new DiscoveryApiError(message, res.status, env?.errors ?? env?.data ?? parsed, code);
  }

  if (isEnvelope(parsed)) return parsed.data as T;
  return parsed as T;
}
