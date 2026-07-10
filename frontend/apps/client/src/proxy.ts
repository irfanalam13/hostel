import { createSecurityProxy } from "@hostel/config";

/**
 * Client-zone security proxy. Shares the exact header logic with the admin
 * zone via @hostel/config.
 *
 * IMPORTANT: the matcher is a POSITIVE list of marketing routes. Every other
 * path falls through to the admin zone via the fallback rewrites in
 * next.config.ts, and the admin app stamps its own per-request CSP nonce on
 * those responses. If this proxy also ran there, the document would carry two
 * CSP headers with two different nonces and the browser would enforce the
 * intersection — rejecting every script.
 */
export const proxy = createSecurityProxy();

export const config = {
  matcher: ["/", "/about", "/privacy", "/security", "/terms"],
};
