/**
 * Shared Playwright fixtures.
 *
 *   test            — base test with the hermetic API mock auto-installed.
 *   authedPage      — a page that lands already authenticated (session seeded
 *                     + /auth/me mocked), saving every spec the login dance.
 *
 * Import { test, expect } from these fixtures instead of "@playwright/test".
 */
import { test as base, expect, type Page } from "@playwright/test";
import { installApiMock, seedSession, type MockOptions } from "./mock-api";

type Fixtures = {
  mockApi: (opts?: MockOptions) => Promise<void>;
  authedPage: Page;
};

export const test = base.extend<Fixtures>({
  // Expose an explicit installer so negative tests can pass {unauthenticated:true}.
  mockApi: async ({ context }, use) => {
    let installed = false;
    await use(async (opts?: MockOptions) => {
      await installApiMock(context, opts);
      installed = true;
    });
    if (!installed) {
      // Default: install a happy-path mock so any plain `page` use still works.
      await installApiMock(context);
    }
  },

  authedPage: async ({ context, baseURL }, use) => {
    await installApiMock(context);
    const page = await context.newPage();
    await seedSession(page, baseURL!);
    await use(page);
    await page.close();
  },
});

export { expect };

/** Wait until the service worker controls the page (it claims clients on activate). */
export async function waitForServiceWorker(page: Page, timeoutMs = 15_000) {
  await page.waitForFunction(
    () => navigator.serviceWorker && navigator.serviceWorker.controller !== null,
    null,
    { timeout: timeoutMs }
  );
}
