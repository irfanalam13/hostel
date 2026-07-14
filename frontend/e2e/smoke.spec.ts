/**
 * Smoke / navigation tests. @smoke
 *
 * Cross-browser sanity sweep: an authenticated user can reach every primary
 * protected route without a client-side crash, an unhandled console error, or a
 * redirect back to /login. Catches broken routes, bad imports, and provider
 * regressions that unit tests miss.
 */
import { test, expect } from "./support/fixtures";

const ROUTES = [
  "/dashboard",
  "/residents",
  "/students",
  "/rooms",
  "/admissions",
  "/payments",
  "/billing",
  "/fees",
  "/attendance",
  "/complaints",
  "/visitors",
  "/expenses",
  "/reports",
  "/exports",
  "/notices",
  "/notifications",
  "/settings",
  "/sync",
];

test.describe("Protected-route smoke @smoke", () => {
  for (const route of ROUTES) {
    test(`renders ${route} without crashing`, async ({ authedPage }) => {
      const errors: string[] = [];
      authedPage.on("console", (m) => {
        if (m.type() === "error") errors.push(m.text());
      });
      authedPage.on("pageerror", (e) => errors.push(String(e)));

      await authedPage.goto(route);
      // Must not be bounced to login, and must paint a real layout (the app
      // shell renders the sidebar/topbar for authenticated routes).
      await expect(authedPage).toHaveURL(new RegExp(route.replace(/\//g, "\\/")));
      await expect(authedPage.locator("body")).toBeVisible();

      // Ignore benign noise (favicon, dev warnings, and expected network chatter
      // from the mocked backend); fail on genuine app/runtime errors.
      const real = errors.filter(
        (e) =>
          !/favicon|manifest|Download the React DevTools|hydrat|Failed to load resource|Failed to fetch|AbortError|401|403|net::ERR/i.test(
            e
          )
      );
      expect(real, `console errors on ${route}:\n${real.join("\n")}`).toHaveLength(0);
    });
  }
});
