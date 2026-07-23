import { authStore } from "@hostel/auth/store";
import { customDomainFromLocation, hostelStore, workspaceFromLocation } from "@hostel/utils";
import { emitUnauthorized } from "@hostel/auth/events";
import { enqueueRequest } from "@hostel/pwa/outbox";
import { captureApiError } from "@hostel/utils";

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
  /** Per-request timeout override (ms). Defaults to API_TIMEOUT_MS. */
  timeoutMs?: number;
};

// Every request is bounded: a stalled backend/socket must reject (so the UI
// can show an error state) instead of leaving the app on a skeleton forever.
export const API_TIMEOUT_MS = (() => {
  const raw = Number(process.env.NEXT_PUBLIC_API_TIMEOUT_MS);
  return Number.isFinite(raw) && raw > 0 ? raw : 30_000;
})();

// Auth-handshake calls (csrf, login, signup, OTP, password reset) get a longer
// budget than data calls: they hit endpoints that can cold-start the backend
// (a spun-down host takes ~30-60s to wake) and do slow work (DB writes + email),
// so a 20-30s ceiling would abort a request that's actually progressing
// ("signal is aborted without reason"). Overridable via NEXT_PUBLIC_AUTH_TIMEOUT_MS.
export const AUTH_TIMEOUT_MS = (() => {
  const raw = Number(process.env.NEXT_PUBLIC_AUTH_TIMEOUT_MS);
  return Number.isFinite(raw) && raw > 0 ? raw : 60_000;
})();

function fetchWithTimeout(
  url: string,
  init: RequestInit,
  timeoutMs: number = API_TIMEOUT_MS
): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  // Respect a caller-provided signal alongside the timeout.
  const callerSignal = init.signal;
  if (callerSignal) {
    if (callerSignal.aborted) controller.abort();
    else callerSignal.addEventListener("abort", () => controller.abort(), { once: true });
  }
  return fetch(url, { ...init, signal: controller.signal }).finally(() => clearTimeout(timer));
}

// Correlates the browser request with the backend's structured request log
// (RequestTimingMiddleware echoes it back as X-Request-ID).
function newRequestId(): string {
  try {
    return crypto.randomUUID().replace(/-/g, "").slice(0, 16);
  } catch {
    return Math.random().toString(36).slice(2, 18);
  }
}

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
    const res = await fetchWithTimeout(
      apiUrl("/auth/csrf/"),
      { credentials: "include", cache: "no-store" },
      AUTH_TIMEOUT_MS,
    );
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
//
// Single-flight: when the access cookie expires, every in-flight request 401s
// at once (dashboard + inbox + heartbeat...). Without a shared promise each
// would POST its own refresh; with rotating refresh tokens the first rotates
// the cookie and the rest send the stale one, failing and dropping a session
// that actually refreshed fine. All concurrent 401s now await ONE refresh.
let refreshInFlight: Promise<boolean> | null = null;

function refreshAccess(): Promise<boolean> {
  if (refreshInFlight) return refreshInFlight;
  refreshInFlight = (async () => {
    try {
      const res = await fetchWithTimeout(apiUrl("/auth/token/refresh/"), {
        method: "POST",
        credentials: "include",
        cache: "no-store",
      });
      return res.ok;
    } catch {
      return false;
    } finally {
      refreshInFlight = null;
    }
  })();
  return refreshInFlight;
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

  // Workspace routing (split-domain bridge): when the SPA is served from a
  // workspace subdomain (everest.myhostel.com) the API may live on another
  // host, so we forward the workspace the page is on. Sourced ONLY from the
  // live hostname — never from stored state — so it always mirrors the URL.
  // The backend resolves the tenant from it pre-auth; for authenticated
  // sessions the JWT's hostel claims remain authoritative.
  const workspace = workspaceFromLocation();
  if (workspace && !headers.has("X-Workspace")) {
    headers.set("X-Workspace", workspace);
  }

  // Custom-domain bridge (Prompt 05): when the page is served from a tenant's
  // own domain (hostel.everest.com) the API — on another host — resolves the
  // tenant from this forwarded hostname. Same live-location-only rule.
  const customHost = customDomainFromLocation();
  if (customHost && !headers.has("X-Tenant-Host")) {
    headers.set("X-Tenant-Host", customHost);
  }

  if (options.auth === false) {
    const hostelCode = authStore.getHostelCode() || hostelStore.getCode();
    if (hostelCode) headers.set("X-Hostel-Code", hostelCode);
  }

  // Trace id: shows up in the backend's per-request log line and is echoed
  // back on the response, so a slow/failed call is greppable server-side.
  if (!headers.has("X-Request-ID")) {
    headers.set("X-Request-ID", newRequestId());
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

async function throwApiError(res: Response, ctx?: { method?: string; url?: string }): Promise<never> {
  let data: unknown = null;
  let msg = `Request failed (${res.status})`;
  // Machine-readable error code from the envelope's meta (e.g. the tenant
  // middleware's workspace_not_found / workspace_suspended / workspace_expired)
  // so callers can branch on the cause instead of string-matching messages.
  let code: string | undefined;

  try {
    data = await res.json();

    if (isEnvelope(data)) {
      // Standard error envelope — surface message, keep original field errors
      // under err.data so forms can still read per-field messages.
      msg = (typeof data.message === "string" && data.message) || msg;
      const metaCode = (data.meta as { code?: unknown } | null | undefined)?.code;
      if (typeof metaCode === "string") code = metaCode;
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

  // Developer tracing: one structured record per backend failure (console in
  // dev, Sentry in prod). User-facing messaging still happens at the caller.
  captureApiError({ method: ctx?.method, url: ctx?.url, status: res.status, detail: msg, data });

  const err = new Error(msg) as Error & { status?: number; data?: unknown; code?: string };
  err.status = res.status;
  err.data = data;
  err.code = code;

  // Subscription entitlement blocks (feature_not_available / plan_limit_reached)
  // carry their machine code in the error body. Broadcast a window event so the
  // upgrade experience (Module 12) can surface a modal from anywhere, without
  // every call site having to handle it. The error still throws as normal.
  const bodyCode =
    data && typeof data === "object" ? (data as { code?: unknown }).code : undefined;
  if (
    typeof window !== "undefined" &&
    (bodyCode === "feature_not_available" || bodyCode === "plan_limit_reached")
  ) {
    window.dispatchEvent(new CustomEvent("entitlement:blocked", { detail: data }));
  }

  throw err;
}

/** Workspace-level rejection codes emitted by the tenant middleware. */
export const WORKSPACE_ERROR_CODES = new Set([
  "workspace_not_found",
  "workspace_suspended",
  "workspace_expired",
  "workspace_pending",
  "workspace_inactive",
]);

/** True when an apiFetch error means the *workspace* (not the user) is blocked. */
export function isWorkspaceError(err: unknown): err is Error & { code: string; status?: number } {
  return (
    !!err &&
    typeof err === "object" &&
    typeof (err as { code?: unknown }).code === "string" &&
    WORKSPACE_ERROR_CODES.has((err as { code: string }).code)
  );
}

// Identical concurrent GETs (e.g. two components mounting and loading the same
// list) share one network request instead of hitting the API twice.
const inflightGets = new Map<string, Promise<unknown>>();

export async function apiFetch<T = unknown>(
  path: string,
  options: ApiOptions = {}
): Promise<T> {
  const method = (options.method || "GET").toUpperCase();
  const url = apiUrl(path, options.params);

  // Dedupe safe, caller-signal-free GETs on the full URL while in flight.
  if (method === "GET" && !options.signal) {
    const existing = inflightGets.get(url);
    if (existing) return existing as Promise<T>;
    const request = executeApiFetch<T>(url, options).finally(() => inflightGets.delete(url));
    inflightGets.set(url, request as Promise<unknown>);
    return request;
  }

  return executeApiFetch<T>(url, options);
}

async function executeApiFetch<T = unknown>(url: string, options: ApiOptions): Promise<T> {
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
  // Every attempt is timeout-bounded (fetchWithTimeout) — a stalled socket
  // rejects instead of pending forever.
  let res: Response;
  const firstInit = buildOptions();
  try {
    res = await fetchWithTimeout(url, firstInit, options.timeoutMs);
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
    res = await fetchWithTimeout(url, buildOptions(), options.timeoutMs);
  }

  // CSRF token stale/missing -> refresh it once and retry.
  if (res.status === 403 && isUnsafe(options.method)) {
    await ensureCsrf(true);
    res = await fetchWithTimeout(url, buildOptions(), options.timeoutMs);
  }

  // Access cookie expired -> try a cookie-based refresh once, then retry.
  // refreshAccess is single-flight: concurrent 401s share one refresh call.
  if (res.status === 401 && options.auth !== false) {
    const refreshed = await refreshAccess();
    if (refreshed) {
      res = await fetchWithTimeout(url, buildOptions(), options.timeoutMs);
    } else {
      // Session is gone; drop the marker and notify the app so the auth layer
      // can redirect to login (once) and clear React state.
      authStore.clear();
      emitUnauthorized();
    }
  }

  if (!res.ok) await throwApiError(res, { method: options.method || "GET", url });
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
  // Downloads get a longer budget than JSON calls, but still can't hang forever.
  const res = await fetchWithTimeout(
    apiUrl(path),
    {
      headers: buildHeaders({}),
      cache: "no-store",
      credentials: "include",
    },
    120_000
  );

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
