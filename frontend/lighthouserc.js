/**
 * Lighthouse CI — performance, accessibility, best-practices, SEO and PWA budgets.
 *
 * Audits the login page — the public surface that doesn't need an authenticated
 * session — which catches perf/a11y/best-practices/SEO regressions in the app
 * shell. (The /offline fallback is deliberately NOT audited: it's served by the
 * service worker and never fires a clean navigation under a standalone Lighthouse
 * run, so every category comes back as NaN.) Run with: `npm run lhci`.
 *
 * Assertions are tuned to be meaningful but not flaky on CI hardware — bump the
 * minScore thresholds as the app is optimised.
 */
const PORT = process.env.LHCI_PORT || 3100;
const BASE = `http://localhost:${PORT}`;

module.exports = {
  ci: {
    collect: {
      // Starts BOTH zones (client on LHCI_PORT, admin on 3101) — /login is
      // served through the client zone's rewrite to the admin app.
      startServerCommand: `node scripts/start-zones.mjs`,
      startServerReadyPattern: "ALL_ZONES_READY",
      startServerReadyTimeout: 120000,
      url: [`${BASE}/login`],
      // One run keeps the job well under its CI timeout; the app's background
      // heartbeat/sync keeps the network busy, so multiple runs each waiting out
      // the load-quiet window pushed the job past 20 min.
      numberOfRuns: 1,
      settings: {
        preset: "desktop",
        // The API lives off-origin and is unreachable here; don't let blocked
        // requests tank the best-practices score.
        skipAudits: ["uses-http2", "canonical"],
        // Hard cap so a page whose network never goes idle can't hang the run.
        maxWaitForLoad: 30000,
      },
    },
    assert: {
      assertions: {
        "categories:performance": ["warn", { minScore: 0.8 }],
        "categories:accessibility": ["error", { minScore: 0.9 }],
        "categories:best-practices": ["warn", { minScore: 0.9 }],
        "categories:seo": ["warn", { minScore: 0.9 }],
        "categories:pwa": ["warn", { minScore: 0.7 }],
        // Hard budgets on the worst offenders.
        "first-contentful-paint": ["warn", { maxNumericValue: 2500 }],
        "total-blocking-time": ["warn", { maxNumericValue: 400 }],
        "cumulative-layout-shift": ["error", { maxNumericValue: 0.1 }],
        "service-worker": "off",
      },
    },
    upload: {
      // Store reports as build artifacts; swap to LHCI server / temporary-public
      // storage if you want shareable URLs.
      target: "filesystem",
      outputDir: ".lighthouseci",
    },
  },
};
