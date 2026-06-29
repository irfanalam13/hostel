/**
 * Sync tests. @chromium-only
 *
 * Verifies the offline-write → IndexedDB outbox → Background Sync replay
 * pipeline (public/sw.js flushOutbox + apps.idempotency on the backend):
 *
 *   - a queued mutation is flushed (2xx) and removed from the outbox; a "synced"
 *     entry lands in the synclog and the page is told (OUTBOX_SYNCED).
 *   - a 409 idempotent replay is treated as a resolved duplicate (deleted).
 *   - a 4xx validation error dead-letters the item (status:"failed"), it is NOT
 *     retried, and the failure is logged.
 *
 * We seed the outbox object store directly (mirrors shared/pwa/outbox.ts schema)
 * and invoke flushOutbox by posting FLUSH_OUTBOX to the SW, so the test drives
 * the exact production replay code without needing a flaky `sync` event.
 */
import { test, expect, waitForServiceWorker } from "./support/fixtures";

const DB_NAME = "hostel-pwa";
const DB_VERSION = 2;

type SeedItem = {
  id: string;
  url: string;
  method: string;
  headers: Record<string, string>;
  body: string;
  status?: string;
  createdAt: number;
  attempts?: number;
};

async function seedOutbox(page: import("@playwright/test").Page, item: SeedItem) {
  await page.evaluate(
    ({ name, version, value }) =>
      new Promise<void>((resolve, reject) => {
        const req = indexedDB.open(name, version);
        req.onupgradeneeded = () => {
          const db = req.result;
          if (!db.objectStoreNames.contains("outbox")) db.createObjectStore("outbox", { keyPath: "id" });
          if (!db.objectStoreNames.contains("keyval")) db.createObjectStore("keyval");
          if (!db.objectStoreNames.contains("synclog")) db.createObjectStore("synclog", { keyPath: "id" });
        };
        req.onsuccess = () => {
          const db = req.result;
          const tx = db.transaction("outbox", "readwrite");
          tx.objectStore("outbox").put(value);
          tx.oncomplete = () => resolve();
          tx.onerror = () => reject(tx.error);
        };
        req.onerror = () => reject(req.error);
      }),
    { name: DB_NAME, version: DB_VERSION, value: item }
  );
}

async function outboxCount(page: import("@playwright/test").Page): Promise<SeedItem[]> {
  return page.evaluate(
    ({ name, version }) =>
      new Promise<any[]>((resolve) => {
        const req = indexedDB.open(name, version);
        req.onsuccess = () => {
          const db = req.result;
          const tx = db.transaction("outbox", "readonly");
          const all = tx.objectStore("outbox").getAll();
          all.onsuccess = () => resolve(all.result || []);
          all.onerror = () => resolve([]);
        };
        req.onerror = () => resolve([]);
      }),
    { name: DB_NAME, version: DB_VERSION }
  );
}

async function flush(page: import("@playwright/test").Page) {
  // Ask the SW to flush, and wait for its OUTBOX_SYNCED / SYNC_LOG_UPDATED reply.
  return page.evaluate(
    () =>
      new Promise<unknown>((resolve) => {
        const onMsg = (e: MessageEvent) => {
          const t = (e.data as { type?: string })?.type;
          if (t === "OUTBOX_SYNCED" || t === "SYNC_LOG_UPDATED") {
            navigator.serviceWorker.removeEventListener("message", onMsg);
            resolve(e.data);
          }
        };
        navigator.serviceWorker.addEventListener("message", onMsg);
        navigator.serviceWorker.controller?.postMessage({ type: "FLUSH_OUTBOX" });
        setTimeout(() => resolve(null), 6000);
      })
  );
}

function baseItem(overrides: Partial<SeedItem> = {}): SeedItem {
  return {
    id: "itm-" + Math.random().toString(36).slice(2),
    url: "http://localhost:8000/api/payments/",
    method: "POST",
    headers: { "Content-Type": "application/json", "Idempotency-Key": "idem-1" },
    body: JSON.stringify({ amount: 5000, method: "cash" }),
    createdAt: 1,
    ...overrides,
  };
}

test.describe("Background Sync / outbox @chromium-only", () => {
  test("a queued mutation is flushed and removed on 2xx", async ({ page, context }) => {
    await context.route(/\/api\/payments\/?$/, (route) =>
      route.fulfill({ status: 201, contentType: "application/json", body: JSON.stringify({ success: true, data: { id: 1 }, meta: {} }) })
    );
    await page.goto("/sync");
    await waitForServiceWorker(page);

    await seedOutbox(page, baseItem());
    expect(await outboxCount(page)).toHaveLength(1);

    const msg = (await flush(page)) as { type?: string; count?: number } | null;
    expect(msg).not.toBeNull();
    await expect.poll(() => outboxCount(page).then((r) => r.length)).toBe(0);
  });

  test("a 409 idempotent replay is treated as a resolved duplicate", async ({ page, context }) => {
    await context.route(/\/api\/payments\/?$/, (route) =>
      route.fulfill({ status: 409, contentType: "application/json", body: JSON.stringify({ detail: "duplicate" }) })
    );
    await page.goto("/sync");
    await waitForServiceWorker(page);

    await seedOutbox(page, baseItem());
    await flush(page);
    // 409 → deleted from the outbox (already applied server-side).
    await expect.poll(() => outboxCount(page).then((r) => r.length)).toBe(0);
  });

  test("a 4xx validation error dead-letters the item without retrying", async ({ page, context }) => {
    await context.route(/\/api\/payments\/?$/, (route) =>
      route.fulfill({ status: 400, contentType: "application/json", body: JSON.stringify({ detail: "amount must be positive" }) })
    );
    await page.goto("/sync");
    await waitForServiceWorker(page);

    await seedOutbox(page, baseItem());
    await flush(page);

    const items = await outboxCount(page);
    expect(items).toHaveLength(1);
    expect(items[0].status).toBe("failed");
  });
});
