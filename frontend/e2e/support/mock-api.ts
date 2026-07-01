/**
 * Hermetic Django API mock for the Playwright suite.
 *
 * The SPA talks to a separately-hosted API (NEXT_PUBLIC_API_BASE_URL, default
 * http://localhost:8000/api). Rather than stand up Postgres + Redis + Celery in
 * CI, we intercept that origin with page.route() and return realistic responses
 * that match the production contract:
 *
 *   - /auth/* endpoints are NOT wrapped (handshake endpoints pass through raw).
 *   - Every other endpoint returns the standard envelope {success, message,
 *     data, meta} that apiClient.ts unwraps.
 *
 * Tests can override any route afterwards (last matching handler wins in
 * Playwright) or pass overrides to installApiMock().
 */
import type { Page, Route, BrowserContext } from "@playwright/test";

export const TEST_HOSTEL_CODE = "HTL-ABC12345";

export const TEST_USER = {
  id: 1,
  username: "warden",
  email: "warden@example.com",
  first_name: "Test",
  last_name: "Warden",
  role: "WARDEN",
  is_staff: true,
  is_active: true,
};

export const TEST_CREDENTIALS = {
  hostelCode: TEST_HOSTEL_CODE,
  username: "warden",
  password: "TestPass!234",
};

type Json = Record<string, unknown> | unknown[] | null;

function envelope(data: Json, message = "OK") {
  return { success: true, message, data, meta: {} };
}

// The SPA fetches a cross-origin API (localhost:3100 → localhost:8000) with
// `credentials: "include"`. A credentialed request REJECTS a wildcard
// `Access-Control-Allow-Origin: *` — the header must echo the exact request
// origin and be paired with `Access-Control-Allow-Credentials: true`. Without
// this every API fetch (and the login POST) is blocked by the browser's CORS
// layer before our handler's body is ever read.
function corsHeaders(route: Route): Record<string, string> {
  const origin = route.request().headers()["origin"] || "*";
  return {
    "access-control-allow-origin": origin,
    "access-control-allow-credentials": "true",
    vary: "Origin",
  };
}

function json(route: Route, status: number, body: unknown) {
  return route.fulfill({
    status,
    contentType: "application/json",
    headers: corsHeaders(route),
    body: JSON.stringify(body),
  });
}

export type MockOptions = {
  /** Force /auth/login/ and /auth/me/ to fail (401) — used by negative tests. */
  unauthenticated?: boolean;
  /** Per-path handlers, keyed by a substring of the pathname. */
  overrides?: Record<string, (route: Route) => unknown>;
  /** Canned dashboard summary numbers. */
  dashboard?: Record<string, number>;
};

/**
 * Install the API mock on a context (so it also covers the service worker's
 * own fetches and any popup). Call from a fixture or at the top of a test.
 */
export async function installApiMock(target: Page | BrowserContext, opts: MockOptions = {}) {
  const dashboard = opts.dashboard ?? {
    residents: 42,
    occupied_beds: 38,
    total_beds: 50,
    dues_this_month: 125000,
    open_complaints: 3,
  };

  await target.route(/https?:\/\/[^/]+\/(api\/)?.*/, async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname.replace(/^\/api/, "");
    const method = request.method();

    // Let same-origin app assets (Next.js, the SW script, icons) load normally.
    const isApiOrigin =
      url.port === "8000" || url.pathname.startsWith("/api/") || url.pathname.startsWith("/auth/");
    if (!isApiOrigin) return route.fallback();

    // Caller-supplied overrides win.
    for (const [needle, handler] of Object.entries(opts.overrides ?? {})) {
      if (path.includes(needle)) return void (await handler(route));
    }

    if (method === "OPTIONS") {
      // CORS preflight: echo the requested method/headers so the credentialed
      // request that follows is allowed through.
      const reqHeaders = request.headers();
      return route.fulfill({
        status: 204,
        headers: {
          ...corsHeaders(route),
          "access-control-allow-methods": "GET,POST,PUT,PATCH,DELETE,OPTIONS",
          "access-control-allow-headers":
            reqHeaders["access-control-request-headers"] ||
            "Content-Type,X-CSRFToken,X-Hostel-Code,Authorization",
          "access-control-max-age": "600",
        },
        body: "",
      });
    }

    // --- Auth handshake (raw, un-enveloped) --------------------------------
    if (path === "/auth/csrf/") return json(route, 200, { csrftoken: "test-csrf-token" });

    if (path === "/auth/login/") {
      if (opts.unauthenticated) {
        return json(route, 400, { detail: "Invalid credentials." });
      }
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        headers: {
          ...corsHeaders(route),
          // Mimic the httpOnly cookie set the backend issues on login.
          "set-cookie": "session_dummy=1; Path=/; SameSite=Lax",
        },
        body: JSON.stringify({ detail: "ok", user: TEST_USER, hostel_code: TEST_HOSTEL_CODE }),
      });
    }

    if (path === "/auth/me/") {
      if (opts.unauthenticated) return json(route, 401, { detail: "Authentication required." });
      return json(route, 200, TEST_USER);
    }

    if (path === "/auth/token/refresh/") {
      return json(route, opts.unauthenticated ? 401 : 200, { detail: "refreshed" });
    }

    if (path === "/auth/logout/") return json(route, 204, {});

    // --- Push subscription endpoints ---------------------------------------
    if (path.startsWith("/push/")) return json(route, 200, envelope({ ok: true }));

    // --- Dashboard summary -------------------------------------------------
    if (path.includes("/dashboard")) return json(route, 200, envelope(dashboard));

    // --- Generic catch-all -------------------------------------------------
    // Reads return an empty paginated list; writes echo back a created object.
    if (["POST", "PUT", "PATCH"].includes(method)) {
      let payload: unknown = {};
      try {
        payload = request.postDataJSON();
      } catch {
        /* non-JSON body */
      }
      return json(route, method === "POST" ? 201 : 200, envelope({ id: 999, ...(payload as object) }, "Saved"));
    }
    if (method === "DELETE") return json(route, 204, {});

    return json(route, 200, envelope({ results: [], count: 0, next: null, previous: null }));
  });
}

/** Seed the localStorage session marker so AuthProvider treats us as logged in. */
export async function seedSession(page: Page, baseURL: string) {
  await page.addInitScript(
    ({ code }) => {
      try {
        localStorage.setItem("session_active", "1");
        localStorage.setItem("hostel_code", code);
        localStorage.setItem("role", "WARDEN");
      } catch {
        /* storage may be unavailable on the very first navigation */
      }
    },
    { code: TEST_HOSTEL_CODE }
  );
}
