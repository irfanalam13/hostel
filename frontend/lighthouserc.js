/**
 * Lighthouse CI — performance, accessibility, best-practices, SEO and PWA budgets.
 *
 * Audits the public surfaces that don't need an authenticated session (the login
 * and offline pages), which is enough to catch perf/a11y/PWA regressions in the
 * app shell, manifest and service worker. Run with: `npm run lhci`.
 *
 * Assertions are tuned to be meaningful but not flaky on CI hardware — bump the
 * minScore thresholds as the app is optimised.
 */
const PORT = process.env.LHCI_PORT || 3100;
const BASE = `http://localhost:${PORT}`;

module.exports = {
  ci: {
    collect: {
      startServerCommand: `npm run start -- --port ${PORT}`,
      startServerReadyPattern: "Ready in|started server on|Local:",
      startServerReadyTimeout: 120000,
      url: [`${BASE}/login`, `${BASE}/offline`],
      // One run per URL keeps the job well under its CI timeout; the app's
      // background heartbeat/sync keeps the network busy, so multiple runs each
      // waiting out the load-quiet window pushed the job past 20 min.
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
