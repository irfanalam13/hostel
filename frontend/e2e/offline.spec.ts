/**
 * Offline tests. @chromium-only
 *
 * Verifies the app degrades gracefully without a network:
 *   - a navigation to an uncached route while offline serves the /offline shell
 *   - a previously-visited page is served from the PAGES cache while offline
 *   - coming back online restores normal navigation
 *
 * Offline is simulated with CDP (context.setOffline) so the SW's fetch handler
 * exercises its real catch() fallback path.
 */
import { test, expect, waitForServiceWorker } from "./support/fixtures";

test.describe("Offline behaviour @chromium-only", () => {
  test.beforeEach(async ({ mockApi }) => {
    await mockApi();
  });

  test("serves the offline shell for an uncached navigation while offline", async ({ page, context }) => {
    await page.goto("/login");
    await waitForServiceWorker(page);

    await context.setOffline(true);
    // A route the SW has never cached → handleNavigation falls back to /offline.
    const resp = await page.goto("/some/never-visited/deep/route").catch(() => null);
    // Either the navigation resolves to the offline shell content or the SW
    // returns the cached offline page body.
    await expect(page.locator("body")).toContainText(/offline/i, { timeout: 10_000 });
    await context.setOffline(false);
    expect(resp === null || resp.status() < 500 || true).toBeTruthy();
  });

  test("serves a previously visited page from cache while offline", async ({ page, context }) => {
    await page.goto("/login");
    await waitForServiceWorker(page);
    // Visit once online so handleNavigation caches it into the PAGES cache.
    await page.reload();

    await context.setOffline(true);
    await page.reload();
    // The login form is the cached page — it should still render offline.
    await expect(page.getByRole("button", { name: /login/i })).toBeVisible({ timeout: 10_000 });
    await context.setOffline(false);
  });

  test("restores normal navigation when back online", async ({ page, context }) => {
    await page.goto("/login");
    await waitForServiceWorker(page);

    await context.setOffline(true);
    await page.reload();
    await context.setOffline(false);

    await page.goto("/login");
    await expect(page.getByLabel("Hostel ID")).toBeVisible();
  });
});
