import { authStore } from "@/shared/auth/auth.store";
import { hostelStore } from "@/shared/lib/hostel";
import { emitUnauthorized } from "@/shared/auth/events";
import { enqueueRequest } from "@/shared/pwa/outbox";

export const API_BASE = (
  process.env.NEXT_PUBLIC_API_BASE_URL?.trim() || "http://localhost:8000/api"
).replace(/\/+$/, "");

type QueryParams = Record<string, string | number | boolean | null | undefined>;

type ApiOptions = RequestInit & {
  auth?: boolean;
  params?: QueryParams;
  /**
   * Opt-in: when an unsafe request (POST/PUT/PATCH/DELETE) fails because the
   * device is offline, persist it to the IndexedDB outbox and let Background
   * Sync replay it later (public/sw.js). The call then rejects with an
   * OfflineQueuedError so the caller can show a "saved, will sync" message.
   * Only JSON (string) bodies are queueable — FormData uploads are not.
   */
  offlineQueue?: boolean;
  /** Idempotency key so an identical retry isn't queued twice. */
  dedupeKey?: string;
  /** Human label shown in the pending-sync UI. */
  queueLabel?: string;
};

type ApiResult<T> = { data: T };

/** Thrown when a request was saved to the offline outbox instead of sent. */
export class OfflineQueuedError extends Error {
  readonly queued = true;
  constructor(message = "You're offline — this change was saved and will sync automatically.") {
    super(message);
    this.name = "OfflineQueuedError";
  }
}

function withParams(url: string, params?: QueryParams) {
  if (!params) return url;

  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") {
      query.set(key, String(value));
    }
  }

  const qs = query.toString();
  return qs ? `${url}${url.includes("?") ? "&" : "?"}${qs}` : url;
}

function apiUrl(path: string, params?: QueryParams) {
  if (path.startsWith("http")) return withParams(path, params);

  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  const baseHasApi = API_BASE.endsWith("/api");
  const pathHasApi = cleanPath === "/api" || cleanPath.startsWith("/api/");

  if (baseHasApi && pathHasApi) {
    return withParams(`${API_BASE}${cleanPath.slice(4) || "/"}`, params);
  }

  if (!baseHasApi && !pathHasApi) {
    return withParams(`${API_BASE}/api${cleanPath}`, params);
  }

  return withParams(`${API_BASE}${cleanPath}`, params);
}

const SAFE_METHODS = ["GET", "HEAD", "OPTIONS", "TRACE"];

function isUnsafe(method?: string) {
  return !SAFE_METHODS.includes((method || "GET").toUpperCase());
}

function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp("(?:^|;\\s*)" + name + "=([^;]+)"));
  return match ? decodeURIComponent(match[1]) : null;
}

// Django CSRF token, needed on unsafe requests once authenticated via cookie.
// In dev (same host) we can often read the csrftoken cookie directly; when the
// SPA is on a different origin we fetch it from /auth/csrf/ (which returns the
// value in its body) and cache it. The csrftoken cookie is still sent to the
// API automatically with credentials:"include".
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
    const res = await fetch(apiUrl("/auth/csrf/"), { credentials: "include", cache: "no-store" });
    const body = (await res.json().catch(() => null)) as { csrftoken?: string } | null;
    csrfToken = body?.csrftoken || readCookie("csrftoken") || null;
  } catch {
    csrfToken = readCookie("csrftoken");
  }
  return csrfToken;
}

// Cookie-based refresh: the refresh token is an httpOnly cookie, so we just
// POST with credentials and let the backend rotate the cookies. Returns whether
// the session was refreshed.
async function refreshAccess(): Promise<boolean> {
  const res = await fetch(apiUrl("/auth/token/refresh/"), {
    method: "POST",
    credentials: "include",
    cache: "no-store",
  });
  return res.ok;
}

function buildHeaders(options: ApiOptions = {}) {
  const headers = new Headers(options.headers || {});

  if (!headers.has("Content-Type") && options.body && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  // Cookie-native auth: the access token rides in an httpOnly cookie sent via
  // credentials:"include" — no Authorization header. On unsafe methods we echo
  // the CSRF token (the cookie itself is enforced server-side).
  if (isUnsafe(options.method) && csrfToken) {
    headers.set("X-CSRFToken", csrfToken);
  }

  if (options.auth === false) {
    const hostelCode = authStore.getHostelCode() || hostelStore.getCode();
    if (hostelCode) headers.set("X-Hostel-Code", hostelCode);
  }

  return headers;
}

// Detects the standard backend envelope: {success, message, data, meta}.
// Auth-handshake endpoints (/auth/*) are intentionally not wrapped, so this
// also safely passes those responses through untouched.
function isEnvelope(
  body: unknown
): body is { success: boolean; message?: string; data: unknown; meta?: unknown; errors?: unknown } {
  return (
    !!body &&
    typeof body === "object" &&
    typeof (body as { success?: unknown }).success === "boolean" &&
    "data" in (body as object) &&
    "meta" in (body as object)
  );
}

async function throwApiError(res: Response): Promise<never> {
  let data: unknown = null;
  let msg = `Request failed (${res.status})`;

  try {
    data = await res.json();

    if (isEnvelope(data)) {
      // Standard error envelope — surface message, keep original field errors
      // under err.data so forms can still read per-field messages.
      msg = (typeof data.message === "string" && data.message) || msg;
      data = data.errors ?? data.data ?? data;
    } else if (data && typeof data === "object") {
      const detail = (data as { detail?: unknown }).detail;
      const firstField = Object.values(data as Record<string, unknown>)[0];
      msg =
        (typeof detail === "string" && detail) ||
        (Array.isArray(firstField) && firstField.length ? String(firstField[0]) : "") ||
        JSON.stringify(data);
    }
  } catch {
    try {
      msg = (await res.text()) || msg;
    } catch {}
  }

  const err = new Error(msg) as Error & { status?: number; data?: unknown };
  err.status = res.status;
  err.data = data;
  throw err;
}

export async function apiFetch<T = unknown>(
  path: string,
  options: ApiOptions = {}
): Promise<T> {
  const url = apiUrl(path, options.params);

  // Make sure we have a CSRF token before any unsafe (state-changing) request.
  if (isUnsafe(options.method)) {
    await ensureCsrf();
  }

  const buildOptions = (): RequestInit => {
    const headers = buildHeaders(options);
    const req: RequestInit = { ...options, headers, cache: "no-store", credentials: "include" };
    delete (req as ApiOptions).params;
    return req;
  };

  // Initial request. For safe (idempotent) methods we retry once on a transient
  // network failure so a flaky connection doesn't surface as a hard error.
  let res: Response;
  const firstInit = buildOptions();
  try {
    res = await fetch(url, firstInit);
  } catch (networkErr) {
    if (isUnsafe(options.method)) {
      // Offline + opt-in → persist to the outbox for Background Sync.
      if (options.offlineQueue && typeof firstInit.body === "string") {
        const headers: Record<string, string> = {};
        (firstInit.headers as Headers).forEach((value, key) => {
          headers[key] = value;
        });
        await enqueueRequest({
          url,
          method: (options.method || "POST").toUpperCase(),
          headers,
          body: firstInit.body,
          dedupeKey: options.dedupeKey,
          label: options.queueLabel,
        });
        throw new OfflineQueuedError();
      }
      throw networkErr;
    }
    await new Promise((r) => setTimeout(r, 300));
    res = await fetch(url, buildOptions());
  }

  // CSRF token stale/missing -> refresh it once and retry.
  if (res.status === 403 && isUnsafe(options.method)) {
    await ensureCsrf(true);
    res = await fetch(url, buildOptions());
  }

  // Access cookie expired -> try a cookie-based refresh once, then retry.
  if (res.status === 401 && options.auth !== false) {
    const refreshed = await refreshAccess();
    if (refreshed) {
      res = await fetch(url, buildOptions());
    } else {
      // Session is gone; drop the marker and notify the app so the auth layer
      // can redirect to login (once) and clear React state.
      authStore.clear();
      emitUnauthorized();
    }
  }

  if (!res.ok) await throwApiError(res);
  if (res.status === 204) return undefined as T;

  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) {
    const body = (await res.json()) as unknown;
    // Unwrap the standard envelope; auth/* and any legacy responses (which are
    // not wrapped) fall through unchanged.
    if (isEnvelope(body)) return body.data as T;
    return body as T;
  }

  return (await res.text()) as T;
}

export const api = {
  async get<T = unknown>(path: string, options: ApiOptions = {}): Promise<ApiResult<T>> {
    return { data: await apiFetch<T>(path, { ...options, method: "GET" }) };
  },

  async post<T = unknown>(
    path: string,
    body?: unknown,
    options: ApiOptions = {}
  ): Promise<ApiResult<T>> {
    return {
      data: await apiFetch<T>(path, {
        ...options,
        method: "POST",
        body: body instanceof FormData ? body : body === undefined ? undefined : JSON.stringify(body),
      }),
    };
  },

  async patch<T = unknown>(
    path: string,
    body?: unknown,
    options: ApiOptions = {}
  ): Promise<ApiResult<T>> {
    return {
      data: await apiFetch<T>(path, {
        ...options,
        method: "PATCH",
        body: body instanceof FormData ? body : body === undefined ? undefined : JSON.stringify(body),
      }),
    };
  },

  async delete<T = unknown>(path: string, options: ApiOptions = {}): Promise<ApiResult<T>> {
    return { data: await apiFetch<T>(path, { ...options, method: "DELETE" }) };
  },
};

export async function apiDownload(path: string, filename?: string) {
  const res = await fetch(apiUrl(path), {
    headers: buildHeaders({}),
    cache: "no-store",
    credentials: "include",
  });

  if (!res.ok) await throwApiError(res);

  let finalName = filename || "download.json";
  const cd = res.headers.get("content-disposition");
  if (!filename && cd) {
    const match = cd.match(/filename="([^"]+)"/);
    if (match?.[1]) finalName = match[1];
  }

  const blob = await res.blob();
  const blobUrl = URL.createObjectURL(blob);

  const a = document.createElement("a");
  a.href = blobUrl;
  a.download = finalName;
  document.body.appendChild(a);
  a.click();
  a.remove();

  URL.revokeObjectURL(blobUrl);
}
