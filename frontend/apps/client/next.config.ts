import path from "node:path";
import type { NextConfig } from "next";

const isDev = process.env.NODE_ENV !== "production";

// The admin zone (apps/admin). In the multi-zone setup the client app owns the
// public domain; any path it does not serve itself (auth, the whole workspace,
// PWA assets) falls through to the admin zone below. Locally that's the admin
// dev/prod server on :3001; on Vercel set ADMIN_ZONE_URL to the admin project's
// deployment URL.
const ADMIN_ZONE_URL = (process.env.ADMIN_ZONE_URL || "http://localhost:3000").replace(/\/$/, "");

// nosniff belongs everywhere; HSTS only over HTTPS (prod).
const baseSecurityHeaders = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  ...(isDev
    ? []
    : [{ key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains; preload" }]),
];

const nextConfig: NextConfig = {
  reactCompiler: true,
  transpilePackages: [
    "@hostel/auth",
    "@hostel/config",
    "@hostel/pwa",
    "@hostel/ui",
    "@hostel/utils",
  ],
  output: process.env.NEXT_OUTPUT_STANDALONE === "1" ? "standalone" : undefined,
  // Monorepo: trace files from the workspace root so the standalone bundle
  // includes hoisted node_modules and workspace packages deterministically.
  outputFileTracingRoot: path.join(__dirname, "../.."),
  poweredByHeader: false,
  productionBrowserSourceMaps: false,
  compiler: {
    removeConsole: isDev ? false : { exclude: ["error", "warn"] },
  },
  experimental: {
    optimizePackageImports: ["lucide-react"],
  },
  async rewrites() {
    return {
      beforeFiles: [],
      afterFiles: [],
      // Anything the marketing app doesn't serve itself belongs to the admin
      // zone: auth pages, the authenticated workspace, sw.js, manifest, icons,
      // and the admin zone's prefixed build assets. Fallback rewrites only run
      // when no client page/asset matched, so marketing routes always win.
      fallback: [
        { source: "/admin-static/:path+", destination: `${ADMIN_ZONE_URL}/admin-static/:path+` },
        { source: "/:path*", destination: `${ADMIN_ZONE_URL}/:path*` },
      ],
    };
  },
  async headers() {
    return [
      {
        source: "/_next/static/:path*",
        headers: [...baseSecurityHeaders, { key: "Cross-Origin-Resource-Policy", value: "same-origin" }],
      },
    ];
  },
};

export default nextConfig;
