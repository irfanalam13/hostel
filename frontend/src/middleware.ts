import { NextResponse, type NextRequest } from "next/server";

/**
 * Security middleware — Phase 10 hardening.
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

// Base64 nonce from the Web Crypto RNG (available on the Edge runtime).
function makeNonce(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  let bin = "";
  for (const b of bytes) bin += String.fromCharCode(b);
  return btoa(bin);
}

function buildCsp(nonce: string, opts: { trustedTypes: boolean }): string {
  const api = apiOrigin();
  // `'strict-dynamic'` makes browsers ignore host allowlists for scripts and
  // trust only the nonce + scripts it loads. `https: http:` + `'unsafe-inline'`
  // are compatibility fallbacks that conforming browsers ignore when a nonce is
  // present. Dev additionally needs eval for React Refresh.
  const script = [
    `'nonce-${nonce}'`,
    "'strict-dynamic'",
    "https:",
    ...(isDev ? ["'unsafe-eval'"] : []),
    "'unsafe-inline'",
  ].join(" ");

  const connect = ["'self'", api, ...(isDev ? ["ws:", "wss:", "http://localhost:8000"] : [])].join(" ");

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
    "report-uri /api/security/csp-report",
    "report-to csp-endpoint",
  ];

  if (opts.trustedTypes) {
    // `default` covers the policy we install; `nextjs`/`react`/`dompurify` are
    // the named policies those libraries create. `'allow-duplicates'` avoids
    // throwing when a policy name is registered more than once across chunks.
    directives.push("require-trusted-types-for 'script'");
    directives.push("trusted-types default nextjs nextjs#bundler react dompurify 'allow-duplicates'");
  }

  if (!isDev) directives.push("upgrade-insecure-requests");

  return directives.join("; ");
}

// Permissions-Policy: explicitly deny every feature the app doesn't use.
const PERMISSIONS_POLICY = [
  "accelerometer=()",
  "ambient-light-sensor=()",
  "autoplay=()",
  "battery=()",
  "camera=()",
  "display-capture=()",
  "document-domain=()",
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
  "interest-cohort=()",
].join(", ");

export function middleware(request: NextRequest) {
  const nonce = makeNonce();
  const enforceTT = process.env.CSP_TT_ENFORCE === "1";

  // Enforced CSP (no Trusted Types unless explicitly flipped on).
  const csp = buildCsp(nonce, { trustedTypes: enforceTT });
  // Report-only CSP always carries Trusted Types so we collect violations even
  // before enforcing — the safe rollout path.
  const cspReportOnly = buildCsp(nonce, { trustedTypes: true });

  // Forward the nonce + CSP on the *request* so Next.js applies the nonce to its
  // injected scripts and Server Components can read it via headers().
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("x-nonce", nonce);
  requestHeaders.set("Content-Security-Policy", csp);

  const res = NextResponse.next({ request: { headers: requestHeaders } });

  res.headers.set("Content-Security-Policy", csp);
  if (!enforceTT) res.headers.set("Content-Security-Policy-Report-Only", cspReportOnly);

  // Reporting endpoint registration (used by report-to above).
  res.headers.set(
    "Reporting-Endpoints",
    `csp-endpoint="/api/security/csp-report"`
  );

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
}

export const config = {
  // Run on documents/pages, not on static assets, the SW, the image optimizer,
  // or well-known files. The CSP report route is excluded so reports aren't
  // themselves subject to a strict CSP redirect.
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|sw.js|manifest.webmanifest|icons/|api/security/csp-report).*)",
  ],
};
