/**
 * Visual regression tests.
 *
 * Pixel-stable snapshots of key surfaces so an unintended CSS/layout change is
 * caught in review. Animations are disabled and dynamic regions are masked so
 * the baselines stay deterministic across runs.
 *
 * First run (or intentional UI change): refresh baselines with
 *   npm run e2e -- --update-snapshots
 * Baselines live in e2e/__screenshots__/ and are committed.
 */
import { test, expect } from "./support/fixtures";

// Tagged @visual: baselines are platform-specific, so this suite is excluded
// from the blocking CI run (which uses --grep-invert @visual) and is instead a
// local/manual gate. Generate/refresh baselines with `npm run e2e:update-snapshots`.
test.describe("Visual regression @visual", () => {
  test.beforeEach(async ({ page }) => {
    // Freeze animations/transitions for stable pixels.
    await page.addStyleTag({
      content: `*,*::before,*::after{transition:none!important;animation:none!important;caret-color:transparent!important}`,
    }).catch(() => {});
  });

  test("login page @smoke", async ({ page, mockApi }) => {
    await mockApi();
    await page.goto("/login");
    await expect(page.getByRole("button", { name: /sign in/i })).toBeVisible();
    await expect(page).toHaveScreenshot("login.png", { fullPage: true, maxDiffPixelRatio: 0.02 });
  });

  test("dashboard", async ({ authedPage }) => {
    await authedPage.goto("/dashboard");
    await authedPage.waitForLoadState("networkidle");
    await expect(authedPage).toHaveScreenshot("dashboard.png", {
      fullPage: true,
      maxDiffPixelRatio: 0.02,
      // Mask number-bearing widgets that may shift with mock data.
      mask: [authedPage.locator("[data-testid='kpi'], .recharts-wrapper")],
    });
  });

  test("offline fallback page", async ({ page, mockApi }) => {
    await mockApi();
    await page.goto("/offline");
    await expect(page).toHaveScreenshot("offline.png", { fullPage: true, maxDiffPixelRatio: 0.02 });
  });
});
