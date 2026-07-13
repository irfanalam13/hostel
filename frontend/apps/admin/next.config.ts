import path from "node:path";
import type { NextConfig } from "next";

const isDev = process.env.NODE_ENV !== "production";

// Per-request document security headers (strict CSP w/ nonce, Trusted Types,
// COOP/COEP, Permissions-Policy) live in src/middleware.ts. The static headers
// below cover only the asset responses the middleware skips, so the two never
// stamp the same header on the same response.

// nosniff belongs everywhere; HSTS only over HTTPS (prod).
const baseSecurityHeaders = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  ...(isDev
    ? []
    : [{ key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains; preload" }]),
];

const nextConfig: NextConfig = {
  reactCompiler: true,
  // Workspace packages are shipped as TypeScript source; Next compiles them.
  transpilePackages: [
    "@hostel/api",
    "@hostel/auth",
    "@hostel/config",
    "@hostel/hooks",
    "@hostel/permissions",
    "@hostel/pwa",
    "@hostel/types",
    "@hostel/ui",
    "@hostel/utils",
  ],
  // Multi-zone: the client (marketing) app owns the domain and rewrites
  // non-marketing paths here. A distinct asset prefix keeps this zone's build
  // assets from colliding with the client zone's /_next/* namespace.
  //
  // Enabled in DEV too (was production-only): the local Nginx gateway
  // (deploy/dev/nginx/gateway.conf) serves both zones on one origin, so admin's
  // /_next/* would collide with the client's. With the prefix, admin assets AND
  // the admin HMR socket live under /admin-static/_next/* — the dev server
  // derives the HMR path from assetPrefix — so the gateway can route
  // /admin-static -> admin and /_next -> client with no collision. Direct
  // :3001 access still works (the dev server strips the prefix).
  assetPrefix: "/admin-static",
  // Allow the Nginx gateway's hostnames to request dev resources (Next 15.3+
  // blocks cross-origin dev asset requests otherwise). Ignored in production.
  allowedDevOrigins: ["localhost", "hostel.local", "127.0.0.1"],
  async rewrites() {
    return {
      beforeFiles: [
        // Serve prefixed asset URLs from the regular build output.
        { source: "/admin-static/_next/:path+", destination: "/_next/:path+" },
      ],
      afterFiles: [],
      fallback: [],
    };
  },
  // NOTE: /admin is no longer redirected to /dashboard — since Prompt 02 it
  // serves the Admin Dashboard Login page (app/(public)/admin).
  // Emit a self-contained server bundle (.next/standalone) ONLY for self-hosted
  // Docker images (the Dockerfile sets NEXT_OUTPUT_STANDALONE=1). On Vercel we
  // leave this off: Vercel has its own deploy pipeline and doesn't need it, and
  // the standalone packager's SRI-manifest copy step breaks when the app is built
  // from a subdirectory (e.g. /vercel/path0/frontend) — see experimental.sri below.
  output: process.env.NEXT_OUTPUT_STANDALONE === "1" ? "standalone" : undefined,
  // Monorepo: trace files from the workspace root so the standalone bundle
  // includes hoisted node_modules and workspace packages deterministically.
  // ONLY for the Docker standalone build. On Vercel this MUST stay unset: with a
  // Root Directory of frontend/apps/admin, a tracing root two levels up makes
  // Vercel's Next builder look for the app's output at apps/admin/.next relative
  // to that root instead of at the Root Directory, failing with
  // "ENOENT ... .next/package.json".
  outputFileTracingRoot:
    process.env.NEXT_OUTPUT_STANDALONE === "1" ? path.join(__dirname, "../..") : undefined,
  // Don't leak the framework or ship browser source maps to production clients.
  poweredByHeader: false,
  productionBrowserSourceMaps: false,
  compiler: {
    // Strip console.* from production bundles (keep error/warn for observability).
    removeConsole: isDev ? false : { exclude: ["error", "warn"] },
  },
  // experimental: {
  //   // Rewrite barrel imports (`import { X } from "lucide-react"`) to per-module
  //   // deep imports so only the icons/charts actually used are bundled. Big win
  //   // for the icon set and recharts on the initial JS payload.
  //   optimizePackageImports: ["lucide-react", "recharts"],
  //   // Subresource Integrity: Next stamps integrity="sha384-…" on its <script>
  //   // tags so a tampered/MITM'd build chunk is rejected by the browser.
  //   sri: { algorithm: "sha384" },
  // },
  experimental: {
    optimizePackageImports: ["lucide-react", "recharts"],
  },
  async headers() {
    return [
      {
        // Immutable, content-hashed build output (same-origin → CORP works with
        // COEP: credentialless from the middleware).
        source: "/_next/static/:path*",
        headers: [...baseSecurityHeaders, { key: "Cross-Origin-Resource-Policy", value: "same-origin" }],
      },
      {
        // Same build output when requested through the zone asset prefix.
        source: "/admin-static/_next/static/:path*",
        headers: [...baseSecurityHeaders, { key: "Cross-Origin-Resource-Policy", value: "same-origin" }],
      },
      {
        // App icons: cache hard for a year; they rarely change.
        source: "/icons/:path*",
        headers: [
          ...baseSecurityHeaders,
          { key: "Cross-Origin-Resource-Policy", value: "same-origin" },
          { key: "Cache-Control", value: "public, max-age=31536000, immutable" },
        ],
      },
      {
        // The service worker must never be cached, so update checks always hit
        // the network; it also needs root scope.
        source: "/sw.js",
        headers: [
          ...baseSecurityHeaders,
          { key: "Cache-Control", value: "no-cache, no-store, must-revalidate" },
          { key: "Service-Worker-Allowed", value: "/" },
        ],
      },
      {
        source: "/manifest.webmanifest",
        headers: [...baseSecurityHeaders, { key: "Cache-Control", value: "public, max-age=3600" }],
      },
    ];
  },
};

export default nextConfig;
