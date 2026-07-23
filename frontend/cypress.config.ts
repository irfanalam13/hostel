import { defineConfig } from "cypress";

/**
 * Cypress — complementary E2E + component suite (Phase 7 QA).
 *
 * Playwright owns the heavy PWA flows (service worker, offline, push, sync) that
 * need CDP and worker.evaluate. Cypress covers the developer-feedback loop:
 *   - fast component tests (mounting React components in a real browser), and
 *   - high-level user-journey E2E (auth, navigation) with cy.intercept mocking.
 *
 * This keeps both tools doing what each is best at instead of duplicating effort.
 */
// Target the admin zone directly (it owns /login, /dashboard, the whole app).
// The two-zone client→admin rewrite is a production/edge concern and a flake
// source under `next start`; see playwright.config.ts for the full rationale.
const PORT = Number(process.env.CY_PORT || 3101);

export default defineConfig({
  e2e: {
    baseUrl: process.env.CY_BASE_URL || `http://localhost:${PORT}`,
    specPattern: "cypress/e2e/**/*.cy.{ts,tsx}",
    supportFile: "cypress/support/e2e.ts",
    fixturesFolder: "cypress/fixtures",
    video: false,
    screenshotOnRunFailure: true,
    retries: { runMode: 2, openMode: 0 },
    defaultCommandTimeout: 8000,
  },
  component: {
    devServer: {
      framework: "next",
      bundler: "webpack",
    },
    specPattern: "cypress/component/**/*.cy.{ts,tsx}",
    supportFile: "cypress/support/component.ts",
  },
});
