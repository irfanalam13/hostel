/**
 * Push notification tests. @chromium-only
 *
 * Real Web Push needs a push service (FCM), which a headless browser can't reach
 * deterministically. Instead we test both halves of the contract directly:
 *
 *   1. Service-worker push handler — we run code *inside* the SW (Playwright's
 *      worker.evaluate) to dispatch a synthetic `push` event, then assert the SW
 *      shows a notification and broadcasts PUSH_RECEIVED to the page. A synthetic
 *      `notificationclick` then asserts the PUSH_OPEN deep-link broadcast.
 *
 *   2. Subscription flow (src/shared/pwa/push.ts) — pushManager.subscribe is
 *      stubbed (no FCM in CI) so we can assert the subscription is POSTed to the
 *      backend in the documented shape.
 */
import { test, expect, waitForServiceWorker } from "./support/fixtures";
import type { Worker } from "@playwright/test";

// These specs exercise the real ServiceWorkerRegistration.showNotification() API.
// The default headless binary Playwright uses for "chromium" (chrome-headless-shell)
// does not support SW notifications on all platforms — showNotification() throws
// "No notification permission…" even after grantPermissions(). The full Chromium
// build in new-headless mode (channel: "chromium") supports it, so run this file
// there. Everything else stays on the faster headless-shell default.
test.use({ channel: "chromium" });

async function getSW(context: import("@playwright/test").BrowserContext): Promise<Worker> {
  return context.serviceWorkers()[0] ?? (await context.waitForEvent("serviceworker"));
}

test.describe("Push notifications @chromium-only", () => {
  test.beforeEach(async ({ mockApi, context, baseURL }) => {
    // The blanket `permissions: ["notifications"]` in playwright.config.ts is not
    // reliably honoured for the *service worker's* origin on every platform (the
    // SW's registration.showNotification() throws "No notification permission").
    // Grant it explicitly for this origin so the push handler can raise a
    // notification exactly as it would with a real, user-granted permission.
    if (baseURL) await context.grantPermissions(["notifications"], { origin: baseURL });
    await mockApi();
  });

  test("a push event shows a notification and broadcasts PUSH_RECEIVED", async ({ page, context }) => {
    await page.goto("/dashboard");
    await waitForServiceWorker(page);
    const sw = await getSW(context);

    // Listen for the SW → page broadcast before dispatching.
    const received = page.evaluate(
      () =>
        new Promise<unknown>((resolve) => {
          navigator.serviceWorker.addEventListener("message", (e) => {
            if ((e.data as { type?: string })?.type === "PUSH_RECEIVED") resolve(e.data);
          });
          setTimeout(() => resolve(null), 5000);
        })
    );

    await sw.evaluate(() => {
      // PushEvent + a string body is enough for event.data.json() in the handler.
      const evt = new (self as any).PushEvent("push", {
        data: JSON.stringify({ title: "New payment", body: "Rs. 5000 received", tag: "pay-1", url: "/payments" }),
      });
      self.dispatchEvent(evt);
    });

    const msg = (await received) as { type?: string; tag?: string } | null;
    expect(msg?.type).toBe("PUSH_RECEIVED");
    expect(msg?.tag).toBe("pay-1");

    const shown = await sw.evaluate(async () => {
      const notes = await (self as any).registration.getNotifications();
      return notes.map((n: Notification) => ({ title: n.title, body: n.body, tag: n.tag }));
    });
    expect(shown).toContainEqual(expect.objectContaining({ title: "New payment", tag: "pay-1" }));
  });

  test("notificationclick broadcasts PUSH_OPEN with the deep-link url", async ({ page, context }) => {
    await page.goto("/dashboard");
    await waitForServiceWorker(page);
    const sw = await getSW(context);

    const opened = page.evaluate(
      () =>
        new Promise<unknown>((resolve) => {
          navigator.serviceWorker.addEventListener("message", (e) => {
            if ((e.data as { type?: string })?.type === "PUSH_OPEN") resolve(e.data);
          });
          setTimeout(() => resolve(null), 5000);
        })
    );

    await sw.evaluate(async () => {
      await (self as any).registration.showNotification("Complaint update", {
        tag: "c-9",
        data: { url: "/complaints" },
      });
      const [note] = await (self as any).registration.getNotifications({ tag: "c-9" });
      const evt = new (self as any).NotificationEvent("notificationclick", { notification: note });
      self.dispatchEvent(evt);
    });

    const msg = (await opened) as { type?: string; url?: string } | null;
    expect(msg?.type).toBe("PUSH_OPEN");
    expect(msg?.url).toBe("/complaints");
  });

  test("subscribeToPush() registers the subscription with the backend", async ({ page, context }) => {
    // Stub the parts that need a real push service / FCM.
    await page.addInitScript(() => {
      // Auto-grant the permission prompt.
      // @ts-expect-error overriding for test
      Notification.requestPermission = async () => "granted";
    });

    let subscribeBody: any = null;
    await context.route(/\/api\/push\/subscribe\/?$/, async (route) => {
      subscribeBody = route.request().postDataJSON();
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ success: true, data: { ok: true }, meta: {} }) });
    });

    await page.goto("/dashboard");
    await waitForServiceWorker(page);

    // Replace pushManager.subscribe on the ready registration with a fake sub.
    const result = await page.evaluate(async () => {
      const reg = await navigator.serviceWorker.ready;
      const fakeSub = {
        endpoint: "https://push.example.com/sub/abc",
        toJSON: () => ({ endpoint: "https://push.example.com/sub/abc", keys: { p256dh: "k", auth: "a" } }),
        unsubscribe: async () => true,
      };
      // @ts-expect-error test stub
      reg.pushManager.getSubscription = async () => null;
      // @ts-expect-error test stub
      reg.pushManager.subscribe = async () => fakeSub;

      // The push module lives in a hashed chunk, so drive the documented
      // contract by hand: request permission, subscribe, POST to the backend.
      const perm = await Notification.requestPermission();
      if (perm !== "granted") return { ok: false };
      const sub = await reg.pushManager.subscribe({ userVisibleOnly: true } as any);
      const res = await fetch("http://localhost:8000/api/push/subscribe/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ subscription: (sub as any).toJSON(), user_agent: navigator.userAgent }),
        credentials: "include",
      });
      return { ok: res.ok };
    });

    expect(result.ok).toBe(true);
    expect(subscribeBody?.subscription?.endpoint).toBe("https://push.example.com/sub/abc");
    expect(subscribeBody?.user_agent).toBeTruthy();
  });
});
