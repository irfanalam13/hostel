import { NextResponse, type NextRequest } from "next/server";
// Pure workspace-host parsing only (edge-safe subpath — avoids pulling the
// whole utils barrel, some of which is browser-only, into the Edge bundle).
import { extractWorkspaceFromHost, isPlatformHost } from "@hostel/utils/workspace";

/**
 * Security proxy — Phase 10 hardening.
 *
 * (Formerly src/middleware.ts — Next.js 16 renamed the "middleware" file
 * convention to "proxy". Same Edge-runtime entry point, new name.)
 *
 * Issues a *strict, per-request* security header set on every document response:
 *
 *   - Strict CSP: a fresh nonce per request + `'strict-dynamic'` so NO
 *     `'unsafe-inline'` script execution is possible. Next.js detects the nonce
 *     in the request's CSP header and stamps it onto its own bootstrap scripts.
 *   - Trusted Types: rolled out in REPORT-ONLY first (so a stray DOM-XSS sink
 *     surfaces in reports without breaking the app). Flip CSP_TT_ENFORCE=1 to
 *     enforce once reports are clean. A default policy is installed client-side
 *     (shared/security/trustedTypes.ts).
 *   - Cross-origin isolation: COOP + COEP + CORP.
 *   - Permissions-Policy: deny every powerful feature we don't use.
 *
 * Static assets, the service worker and the image optimizer are excluded (see
 * `config.matcher`) — they don't execute page script and the SW needs its own
 * cache headers from next.config.ts.
 */

const isDev = process.env.NODE_ENV !== "production";

function apiOrigin(): string {
  try {
    return new URL(process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api").origin;
  } catch {
    return "http://localhost:8000";
  }
}

// The AI (ML_hostel) service origin, when it is hosted on its own domain (prod).
// The admin app opens the assistant's SSE stream directly against it, so its
// origin must be allowed in connect-src. Empty in dev (same-origin via the
// nginx gateway at /ai), so nothing is added there.
function mlOrigin(): string | null {
  const url = process.env.NEXT_PUBLIC_ML_BASE_URL;
  if (!url) return null;
  try {
    return new URL(url).origin;
  } catch {
    return null;
  }
}

// Base64 nonce from the Web Crypto RNG (available on the Edge runtime).
function makeNonce(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  let bin = "";
  for (const b of bytes) bin += String.fromCharCode(b);
  return btoa(bin);
}

// Trusted-Types directives, shared between the enforced policy (when
// CSP_TT_ENFORCE=1) and the report-only soak policy.
//   `default` covers the policy we install; `nextjs`/`react`/`dompurify` are the
//   named policies those libraries create. `'allow-duplicates'` avoids throwing
//   when a policy name is registered more than once across chunks.
const TRUSTED_TYPES_DIRECTIVES = [
  "require-trusted-types-for 'script'",
  "trusted-types default nextjs nextjs#bundler react dompurify 'allow-duplicates'",
];

// Reporting sinks. `report-uri` is deprecated but kept for Firefox/Safari, which
// don't yet honour the Reporting API `report-to`; conforming browsers use
// `report-to` and ignore `report-uri` without warning.
const REPORT_DIRECTIVES = ["report-uri /api/security/csp-report", "report-to csp-endpoint"];

// The enforced document CSP.
function buildCsp(nonce: string, opts: { trustedTypes: boolean; https: boolean }): string {
  const api = apiOrigin();
  // `'strict-dynamic'` makes browsers ignore host allowlists for scripts and
  // trust only the nonce + scripts it loads. `https:` + `'unsafe-inline'` are
  // compatibility fallbacks that conforming (CSP3) browsers ignore when a nonce
  // is present — this is the OWASP "strict CSP" pattern, and the console note
  // about `'unsafe-inline'` being ignored is expected, not a misconfiguration.
  // Dev additionally needs eval for React Refresh.
  const script = [
    `'nonce-${nonce}'`,
    "'strict-dynamic'",
    "https:",
    ...(isDev ? ["'unsafe-eval'"] : []),
    "'unsafe-inline'",
  ].join(" ");

  const ml = mlOrigin();
  const connect = [
    "'self'",
    api,
    ...(ml ? [ml] : []),
    ...(isDev ? ["ws:", "wss:", "http://localhost:8000"] : []),
  ].join(" ");

  const directives = [
    "default-src 'self'",
    `script-src ${script}`,
    // Tailwind injects inline <style>; styles can't run script so this is safe.
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob:",
    "font-src 'self' data:",
    `connect-src ${connect}`,
    "worker-src 'self'",
    "manifest-src 'self'",
    "frame-src 'none'",
    "child-src 'none'",
    "base-uri 'none'",
    "form-action 'self'",
    "frame-ancestors 'none'",
    "object-src 'none'",
    ...REPORT_DIRECTIVES,
  ];

  if (opts.trustedTypes) directives.push(...TRUSTED_TYPES_DIRECTIVES);

  // `upgrade-insecure-requests` must only be sent when the page is actually
  // served over HTTPS. Gating on NODE_ENV is wrong: a production build served
  // over plain HTTP (e.g. DEBUG=False locally, or behind a non-TLS proxy) would
  // then tell the browser to upgrade http://<api>:8000 fetches to https://,
  // which the API doesn't speak — silently breaking every API call. So we key
  // off the real request scheme instead.
  if (opts.https) directives.push("upgrade-insecure-requests");

  return directives.join("; ");
}

// Minimal report-only policy used purely to soak Trusted-Types violations before
// flipping CSP_TT_ENFORCE=1. It intentionally does NOT mirror the enforced
// policy: the enforced policy already reports its own script/style/etc.
// violations, so cloning it here would double-report every violation. It also
// omits `upgrade-insecure-requests` (ignored + warned in report-only mode).
function buildTrustedTypesReportOnlyCsp(): string {
  return [...TRUSTED_TYPES_DIRECTIVES, ...REPORT_DIRECTIVES].join("; ");
}

// Permissions-Policy: explicitly deny every powerful feature the app doesn't
// use. Only modern, browser-recognised directives are listed — deprecated /
// unrecognised ones (ambient-light-sensor, battery, document-domain,
// interest-cohort) are intentionally omitted because they only produce
// "Unrecognized feature" console warnings without adding protection.
const PERMISSIONS_POLICY = [
  "accelerometer=()",
  "autoplay=()",
  "camera=()",
  "display-capture=()",
  "encrypted-media=()",
  "fullscreen=(self)",
  "geolocation=()",
  "gyroscope=()",
  "hid=()",
  "idle-detection=()",
  "magnetometer=()",
  "microphone=()",
  "midi=()",
  "payment=()",
  "picture-in-picture=()",
  "publickey-credentials-get=()",
  "screen-wake-lock=()",
  "serial=()",
  "usb=()",
  "xr-spatial-tracking=()",
  "browsing-topics=()",
].join(", ");


/**
 * Build the Edge proxy handler. Each app keeps its own `config.matcher` (Next
 * requires that export to be statically analyzable, so it cannot live here),
 * but shares this handler so both zones emit an identical, always-in-sync
 * security header set.
 */
export function createSecurityProxy() {
  return function proxy(request: NextRequest) {
    const nonce = makeNonce();
    const enforceTT = process.env.CSP_TT_ENFORCE === "1";
    // True only when the document is genuinely served over TLS. Behind a reverse
    // proxy the edge sees http internally, so trust the forwarded scheme too.
    const https =
      request.headers.get("x-forwarded-proto") === "https" ||
      request.nextUrl.protocol === "https:";

    // Enforced CSP (no Trusted Types unless explicitly flipped on).
    const csp = buildCsp(nonce, { trustedTypes: enforceTT, https });
    // Report-only CSP carries ONLY the Trusted-Types directives so we soak those
    // violations before enforcing — the safe rollout path — without duplicating
    // the enforced policy's reports.
    const cspReportOnly = buildTrustedTypesReportOnlyCsp();

    // Forward the nonce + CSP on the *request* so Next.js applies the nonce to
    // its injected scripts and Server Components can read it via headers().
    const requestHeaders = new Headers(request.headers);
    requestHeaders.set("x-nonce", nonce);
    requestHeaders.set("Content-Security-Policy", csp);

    // Multi-tenant workspace routing: when the document is served from a
    // workspace subdomain (everest.<TENANT_BASE_DOMAIN>), expose the slug to
    // Server Components / route handlers via headers(). Derived strictly from
    // the Host header — a client-sent x-workspace on the document request is
    // discarded so SSR can never be steered at a different tenant.
    requestHeaders.delete("x-workspace");
    requestHeaders.delete("x-tenant-host");
    const docHost = request.headers.get("host") || "";
    const workspace = extractWorkspaceFromHost(docHost);
    if (workspace) {
      requestHeaders.set("x-workspace", workspace);
    } else if (docHost && !isPlatformHost(docHost)) {
      // Tenant custom domain (Prompt 05) — expose it to Server Components.
      requestHeaders.set("x-tenant-host", docHost.split(":")[0].toLowerCase());
    }

    const res = NextResponse.next({ request: { headers: requestHeaders } });

    res.headers.set("Content-Security-Policy", csp);
    if (!enforceTT) res.headers.set("Content-Security-Policy-Report-Only", cspReportOnly);

    // Reporting endpoint registration (used by report-to above).
    res.headers.set("Reporting-Endpoints", `csp-endpoint="/api/security/csp-report"`);

    // Cross-origin isolation.
    res.headers.set("Cross-Origin-Opener-Policy", "same-origin");
    res.headers.set("Cross-Origin-Embedder-Policy", "credentialless");
    res.headers.set("Cross-Origin-Resource-Policy", "same-origin");

    // Defence-in-depth headers (also set statically in next.config.ts for assets).
    res.headers.set("X-Content-Type-Options", "nosniff");
    res.headers.set("X-Frame-Options", "DENY");
    res.headers.set("Referrer-Policy", "strict-origin-when-cross-origin");
    res.headers.set("Permissions-Policy", PERMISSIONS_POLICY);
    res.headers.set("Origin-Agent-Cluster", "?1");

    return res;
  };
}
