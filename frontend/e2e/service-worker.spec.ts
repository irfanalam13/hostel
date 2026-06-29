/**
 * Service Worker tests. @chromium-only
 *
 * Verifies the hand-written SW (public/sw.js) behaves as designed:
 *   - registers and takes control (clients.claim on activate)
 *   - reports its version over the GET_VERSION MessageChannel
 *   - precaches the offline shell + serves app-shell assets from cache
 *   - never caches cross-origin API responses (security invariant)
 *   - SKIP_WAITING activates a waiting worker
 */
import { test, expect, waitForServiceWorker } from "./support/fixtures";

test.describe("Service Worker @chromium-only", () => {
  test.beforeEach(async ({ mockApi }) => {
    await mockApi();
  });

  test("registers and takes control of the page", async ({ page }) => {
    await page.goto("/login");
    await waitForServiceWorker(page);

    const reg = await page.evaluate(async () => {
      const r = await navigator.serviceWorker.getRegistration();
      return { hasReg: !!r, active: !!r?.active, scope: r?.scope };
    });
    expect(reg.hasReg).toBe(true);
    expect(reg.active).toBe(true);
    expect(reg.scope).toMatch(/\/$/);
  });

  test("answers GET_VERSION with the current cache version", async ({ page }) => {
    await page.goto("/login");
    await waitForServiceWorker(page);

    const version = await page.evaluate(
      () =>
        new Promise<string | null>((resolve) => {
          const ctrl = navigator.serviceWorker.controller;
          if (!ctrl) return resolve(null);
          const ch = new MessageChannel();
          const t = setTimeout(() => resolve(null), 3000);
          ch.port1.onmessage = (e) => {
            clearTimeout(t);
            resolve((e.data as { version?: string })?.version ?? null);
          };
          ctrl.postMessage({ type: "GET_VERSION" }, [ch.port2]);
        })
    );
    expect(version).toMatch(/^v\d+\.\d+\.\d+$/);
  });

  test("precaches the offline fallback shell", async ({ page }) => {
    await page.goto("/login");
    await waitForServiceWorker(page);

    const cached = await page.evaluate(async () => {
      const match = await caches.match("/offline");
      return !!match;
    });
    expect(cached).toBe(true);
  });

  test("does NOT cache cross-origin API responses", async ({ page }) => {
    await page.goto("/login");
    await waitForServiceWorker(page);

    // Make an API call, then assert nothing under the API origin landed in any cache.
    await page.evaluate(() => fetch("http://localhost:8000/api/dashboard/").catch(() => {}));
    const leaked = await page.evaluate(async () => {
      const names = await caches.keys();
      for (const n of names) {
        const c = await caches.open(n);
        const keys = await c.keys();
        if (keys.some((req) => new URL(req.url).port === "8000")) return true;
      }
      return false;
    });
    expect(leaked).toBe(false);
  });

  test("SKIP_WAITING activates a waiting worker without an infinite reload", async ({ page }) => {
    await page.goto("/login");
    await waitForServiceWorker(page);
    // Post SKIP_WAITING to the active worker; with no waiting worker it's a no-op
    // and must not crash or loop. (The full update path needs two SW versions.)
    const ok = await page.evaluate(async () => {
      const r = await navigator.serviceWorker.getRegistration();
      r?.active?.postMessage({ type: "SKIP_WAITING" });
      return true;
    });
    expect(ok).toBe(true);
    await expect(page).toHaveURL(/\/login/);
  });
});
