import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright — the primary end-to-end suite (Phase 7 QA).
 *
 * It drives a real Chromium against a real Next.js server. The Django API is
 * mocked at the network layer (see e2e/support/mock-api.ts) so the suite is
 * hermetic and deterministic in CI — no Postgres/Redis/Celery required. A
 * separate `live` project (PW_LIVE=1) can run the same specs against a real
 * backend for smoke verification before a release.
 *
 * Coverage map (Phase 7 checklist):
 *   - Authentication ........ e2e/auth.spec.ts
 *   - Service Worker ........ e2e/service-worker.spec.ts
 *   - Offline ............... e2e/offline.spec.ts
 *   - Push notifications .... e2e/push.spec.ts
 *   - Sync (outbox) ......... e2e/sync.spec.ts
 *   - Regression (visual) ... e2e/regression.spec.ts
 *   - Smoke / navigation .... e2e/smoke.spec.ts
 */

const PORT = Number(process.env.PW_PORT || 3100);
const BASE_URL = process.env.PW_BASE_URL || `http://localhost:${PORT}`;
const isLive = process.env.PW_LIVE === "1";
const isCI = !!process.env.CI;

export default defineConfig({
  testDir: "./e2e",
  // SW/offline/push tests serialise per-file; never share a worker across files.
  fullyParallel: true,
  forbidOnly: isCI,
  retries: isCI ? 2 : 0,
  workers: isCI ? 2 : undefined,
  timeout: 60_000,
  expect: { timeout: 10_000 },

  reporter: isCI
    ? [["github"], ["html", { open: "never" }], ["junit", { outputFile: "playwright-report/junit.xml" }]]
    : [["html", { open: "never" }], ["list"]],

  use: {
    baseURL: BASE_URL,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    // Service workers must NOT be bypassed — the PWA tests need them registered.
    serviceWorkers: "allow",
  },

  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        // Grant notifications up-front so the push tests can call
        // Notification.requestPermission() without a manual prompt.
        permissions: ["notifications"],
      },
    },
    // Cross-browser regression coverage (visual + smoke only — WebKit/Firefox
    // don't expose the Background Sync API, so PWA specs opt out via tags).
    {
      name: "firefox",
      use: { ...devices["Desktop Firefox"] },
      grepInvert: /@chromium-only/,
    },
    {
      name: "mobile",
      use: { ...devices["Pixel 7"] },
      grep: /@mobile|@smoke/,
    },
  ],

  // Build once, then `next start` on an isolated port. In live mode we assume a
  // server is already running and just reuse it.
  webServer: isLive
    ? undefined
    : {
        command: `npm run build && npm run start -- --port ${PORT}`,
        url: BASE_URL,
        timeout: 240_000,
        reuseExistingServer: !isCI,
        env: {
          // Point the app at the origin we intercept in mock-api.ts.
          NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api",
          NEXT_PUBLIC_VAPID_PUBLIC_KEY:
            process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY ||
            // A throwaway valid VAPID public key so pushConfigured() is true in tests.
            "BEl62iUYgUivxIkv69yViEuiBIa-Ib9-Skv_jd9MgSjdfsajklfdsjklfdsjklfdsajklfdsjklfdsjklfdsabc",
        },
      },
});
