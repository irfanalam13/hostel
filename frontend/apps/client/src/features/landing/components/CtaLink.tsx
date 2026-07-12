import React from "react";
import Link from "next/link";

/**
 * Landing CTAs point at two different Next.js zones:
 *   - the marketing app itself (this "client" zone): "/", in-page anchors
 *     ("#faq") and root-relative anchors ("/#pricing")
 *   - the admin zone (apps/admin), reached via the fallback rewrite in
 *     next.config.ts: "/signup", "/login", "/dashboard", …
 *
 * Multi-zone SOFT navigation is not supported. A <Link> to an admin-zone route
 * fires an RSC prefetch/navigation ("/signup?_rsc=…") that carries THIS zone's
 * router-state-tree; the admin server can't render against a foreign tree and
 * responds 500, so the click dead-ends on the error boundary ("Something went
 * wrong") and the page never changes. Jumps across zones must be a full-document
 * navigation via a plain <a>.
 *
 * CtaLink keeps <Link>'s fast soft-nav for same-zone targets and falls back to
 * <a> for anything that crosses into another zone — so a new CTA can't silently
 * reintroduce the broken soft-nav.
 *
 * DEV-ONLY ORIGIN: in production the admin zone is reached by a same-origin path
 * ("/signup") that the edge rewrites to the admin deployment. In development the
 * client dev server (:3000) reverse-proxies admin routes to the admin dev server
 * — but proxying breaks the admin app's Turbopack dev runtime/HMR, so the admin
 * page renders yet never HYDRATES (forms fall back to native GET submits and the
 * screen looks stuck / infinitely refreshing). The dev fix is to send cross-zone
 * links straight to the admin dev server's own origin. NEXT_PUBLIC_ADMIN_ORIGIN
 * carries that origin in dev and is empty in prod (links stay relative).
 */
const CLIENT_ZONE_ROUTES = ["/about", "/privacy", "/terms", "/security"];

// e.g. "http://localhost:3001" in dev; "" in prod (same-origin, edge-routed).
const ADMIN_ORIGIN = (process.env.NEXT_PUBLIC_ADMIN_ORIGIN || "").replace(/\/+$/, "");

function isSameZone(href: string): boolean {
  // In-page anchors and the marketing root are served by this app.
  if (href.startsWith("#") || href === "/" || href.startsWith("/#")) return true;
  // A real client-zone route (ignore any query/hash when matching).
  const path = href.split(/[?#]/)[0];
  return CLIENT_ZONE_ROUTES.includes(path);
}

type CtaLinkProps = React.ComponentPropsWithoutRef<"a"> & { href: string };

export function CtaLink({ href, children, ...props }: CtaLinkProps) {
  if (isSameZone(href)) {
    return (
      <Link href={href} {...props}>
        {children}
      </Link>
    );
  }
  // Cross-zone → hard navigation. Target the admin origin when configured (dev),
  // otherwise keep the relative path (prod, edge-routed). Never rewrite an href
  // that is already absolute.
  const isAbsolute = /^https?:\/\//.test(href);
  const target = isAbsolute || !ADMIN_ORIGIN ? href : ADMIN_ORIGIN + href;
  return (
    <a href={target} {...props}>
      {children}
    </a>
  );
}
