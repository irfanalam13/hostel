// Centralised client-side error logging. Sentry-ready: if a Sentry SDK is
// present on `window.Sentry` (loaded via a script/loader) OR a DSN is
// configured, errors are forwarded with user context; otherwise we fall back
// to the console. This is the single hook point the whole app logs through so
// swapping in a real provider later is a one-file change.

type UserContext = {
  id?: string | number | null;
  role?: string | null;
  hostel?: string | null;
};

type SentryLike = {
  captureException: (err: unknown, ctx?: unknown) => void;
  setUser?: (user: unknown) => void;
};

let userContext: UserContext = {};

function getSentry(): SentryLike | null {
  if (typeof window === "undefined") return null;
  const s = (window as unknown as { Sentry?: SentryLike }).Sentry;
  return s && typeof s.captureException === "function" ? s : null;
}

const SENTRY_DSN =
  (typeof process !== "undefined" && process.env?.NEXT_PUBLIC_SENTRY_DSN) || "";

/** Attach the signed-in user so every captured error is attributable. */
export function setUserContext(ctx: UserContext) {
  userContext = { ...ctx };
  getSentry()?.setUser?.({ id: ctx.id ?? undefined, role: ctx.role, hostel: ctx.hostel });
}

export function clearUserContext() {
  userContext = {};
  getSentry()?.setUser?.(null);
}

type CaptureExtra = Record<string, unknown>;

/**
 * Log an error to the monitoring system. Never throws — logging must not be
 * able to crash the UI it is trying to report on.
 */
export function captureError(error: unknown, extra?: CaptureExtra) {
  try {
    const sentry = getSentry();
    const context = { user: userContext, ...(extra ? { extra } : {}) };

    if (sentry) {
      sentry.captureException(error, context);
      return;
    }

    // No SDK wired up yet — keep a structured console record (and a hint that a
    // DSN exists but the SDK hasn't loaded, which is a misconfiguration).
    const tag = SENTRY_DSN ? "[monitoring:sentry-dsn-set-but-sdk-missing]" : "[monitoring]";
    console.error(tag, error, context);
  } catch {
    // Swallow — logging failures must be silent.
  }
}

/** Capture a non-exception message (e.g. a handled API failure). */
export function captureMessage(message: string, extra?: CaptureExtra) {
  captureError(new Error(message), { handled: true, ...extra });
}

type ApiErrorContext = {
  method?: string;
  url?: string;
  status?: number;
  /** The backend's error detail/message, already extracted by the API client. */
  detail?: string;
  /** Raw error body (field errors etc.), for debugging. */
  data?: unknown;
};

/**
 * Trace a backend API failure for developers. Every failed `apiFetch` funnels
 * through here, so a single structured record — method, endpoint, HTTP status
 * and the backend's own detail — is available in the browser console (dev) and
 * forwarded to Sentry (prod), without each component having to log it.
 */
export function captureApiError(ctx: ApiErrorContext) {
  try {
    const { method = "GET", url = "", status = 0, detail = "", data } = ctx;
    const label = `${method.toUpperCase()} ${url} → ${status}`;
    const sentry = getSentry();
    if (sentry) {
      sentry.captureException(new Error(`API ${label}: ${detail}`), {
        user: userContext,
        extra: { api_error: true, method, url, status, detail, data },
      });
      return;
    }
    // Dev/no-SDK: a single grouped, greppable record devs can trace from.
    console.error(`[api-error] ${label}`, { detail, data });
  } catch {
    // Swallow — tracing must never crash the request path.
  }
}
