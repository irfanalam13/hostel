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
  // Emit a self-contained server bundle (.next/standalone) for a small,
  // dependency-free production Docker image.
  output: "standalone",
  // Don't leak the framework or ship browser source maps to production clients.
  poweredByHeader: false,
  productionBrowserSourceMaps: false,
  compiler: {
    // Strip console.* from production bundles (keep error/warn for observability).
    removeConsole: isDev ? false : { exclude: ["error", "warn"] },
  },
  experimental: {
    // Rewrite barrel imports (`import { X } from "lucide-react"`) to per-module
    // deep imports so only the icons/charts actually used are bundled. Big win
    // for the icon set and recharts on the initial JS payload.
    optimizePackageImports: ["lucide-react", "recharts"],
    // Subresource Integrity: Next stamps integrity="sha384-…" on its <script>
    // tags so a tampered/MITM'd build chunk is rejected by the browser.
    sri: { algorithm: "sha384" },
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
