import { createSecurityProxy } from "@hostel/config";

/**
 * Admin-zone security proxy (formerly the monolith's src/middleware.ts). The
 * header logic is shared with the client zone via @hostel/config so both apps
 * always emit the same strict-CSP/Trusted-Types/isolation header set.
 */
export const proxy = createSecurityProxy();

export const config = {
  // Run on documents/pages, not on static assets (plain or zone-prefixed), the
  // SW, the image optimizer, or well-known files. The CSP report route is
  // excluded so reports aren't themselves subject to a strict CSP redirect.
  matcher: [
    "/((?!_next/static|_next/image|admin-static/|favicon.ico|sw.js|manifest.webmanifest|icons/|screenshots/|api/security/csp-report).*)",
  ],
};
