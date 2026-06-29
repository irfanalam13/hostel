# Progressive Web App (PWA) — Architecture & Operations

This document describes the PWA layer added to the Hostel Management System
frontend. It is a **single shared codebase**: the website and the installed app
run the same Next.js build, the same Django API, the same cookie-based auth and
the same deployment pipeline. No code was duplicated.

---

## 1. File map

| Area | File | Purpose |
| --- | --- | --- |
| Manifest | `src/app/manifest.ts` | Typed `manifest.webmanifest` (icons, shortcuts, screenshots, categories, `display_override`, `id`). Auto-linked by Next. |
| Metadata | `src/app/layout.tsx` | `metadata` + `viewport` (theme-color light/dark, `viewport-fit=cover`, apple-web-app, icons). |
| Service worker | `public/sw.js` | Caching strategies, offline fallback, update lifecycle, Background Sync, Push. |
| Offline page | `src/app/offline/page.tsx` | Static fallback served when a navigation fails offline. |
| Assets | `scripts/generate-pwa-assets.mjs` | Regenerates all icons + screenshots from one SVG (`node scripts/generate-pwa-assets.mjs`). |
| Registration | `src/shared/pwa/register.ts` | SW registration + safe update detection (`controllerchange` reload guard). |
| IndexedDB | `src/shared/pwa/db.ts` | Promise wrapper over the `hostel-pwa` DB (`outbox` + `keyval` stores). |
| Offline queue | `src/shared/pwa/outbox.ts` | Enqueue mutations, register Background Sync, auto-flush on reconnect. |
| Push | `src/shared/pwa/push.ts` | Subscribe/unsubscribe + register subscription with the backend. |
| Provider | `src/shared/providers/PwaProvider.tsx` | Wires all of the above; exposes `usePwa()`. |
| UI | `src/shared/pwa/components/*` | Install prompt/button, update banner, offline indicator, settings card. |
| Headers | `next.config.ts` | CSP + security headers; `no-cache` for `/sw.js`. |

---

## 2. Caching strategies (`public/sw.js`)

Cross-origin requests (the Django API on a **different origin**) are never
intercepted or cached — credentials and private API data are never stored.

| Resource | Strategy | Cache |
| --- | --- | --- |
| Navigations (HTML) | Network-first + navigation preload → cached page → `/offline` | `hms-pages-*` |
| `/_next/static/*`, fonts | Cache-first (content-hashed, immutable) | `hms-runtime-*` |
| Images | Stale-while-revalidate (trimmed to 60) | `hms-images-*` |
| Scripts / styles / other GET | Stale-while-revalidate | `hms-runtime-*` |
| App shell (`/offline`, manifest, icons) | Precached on install | `hms-precache-*` |

Caches are versioned by `VERSION` in `sw.js`. On `activate`, any cache whose key
doesn't match the current version is deleted. Image and page caches are trimmed
(FIFO) to bound storage.

---

## 3. Update flow

1. A deploy ships a new `sw.js` (served with `Cache-Control: no-cache`).
2. The browser installs it; it enters **waiting**.
3. `register.ts` detects this and fires `onUpdateAvailable` → `UpdateBanner`
   shows **"Update available"**.
4. User clicks **Update now** → `applyUpdate()` posts `SKIP_WAITING`.
5. The new worker activates → `controllerchange` → the page reloads **once**
   (guarded against reload loops).

To force the version bump, change `VERSION` in `public/sw.js`.

---

## 4. Offline writes (IndexedDB + Background Sync)

**Opt-in** per request so existing flows are unchanged. Pass `offlineQueue: true`
to the API client:

```ts
import { api, OfflineQueuedError } from "@/shared/api/apiClient";

try {
  await api.post("/payments/", payload, {
    offlineQueue: true,
    dedupeKey: `payment-${idempotencyId}`, // prevents double submission
    queueLabel: "Record payment",
  });
} catch (err) {
  if (err instanceof OfflineQueuedError) {
    toast.info("Saved offline — will sync when you reconnect.");
  } else {
    throw err;
  }
}
```

Flow: on a network failure the request (URL, method, headers incl. CSRF, JSON
body) is written to the `outbox` store and a Background Sync (`hms-outbox-sync`)
is registered. The SW's `sync` handler (`flushOutbox`) replays entries oldest-
first when connectivity returns: `2xx`/`4xx` are removed (success / permanently
rejected); `5xx`/network errors stop the run to retry later. On success the SW
broadcasts `OUTBOX_SYNCED`, which the provider surfaces as a toast.

Where Background Sync is unsupported (Safari, Firefox), the queue is flushed on
the next `online` event instead.

### IndexedDB schema (`hostel-pwa`, v1)
- `outbox` (keyPath `id`) — queued mutations: `{ id, url, method, headers, body, createdAt, dedupeKey?, label? }`.
- `keyval` — generic store for preferences, drafts, recently-viewed pages, cached
  API snapshots (`kvGet`/`kvSet`/`kvDelete`).

> The schema is duplicated in `public/sw.js` because a service worker can't
> import app modules. Keep the two in sync if you bump `DB_VERSION`.

---

## 5. Push notifications

**Frontend** is complete (`push.ts` + the toggle in Settings). It is inert until
a VAPID public key is provided and a backend implements the contract.

1. Generate keys: `npx web-push generate-vapid-keys`.
2. Set env (see `.env.example`): `NEXT_PUBLIC_VAPID_PUBLIC_KEY` (browser) and
   `VAPID_PRIVATE_KEY` + `VAPID_SUBJECT` (backend only).
3. Implement the backend contract:

```
POST /api/push/subscribe/    body: { subscription: <PushSubscription JSON>, user_agent }
POST /api/push/unsubscribe/  body: { endpoint }
```

Store subscriptions per user; send with `pywebpush` using the private key. The SW
`push` handler renders `{ title, body, icon, url, tag, requireInteraction }` and
`notificationclick` deep-links to `data.url` (focuses an existing tab if open).

---

## 6. Install flow

`PwaProvider` captures `beforeinstallprompt`. `InstallPrompt` shows a dismissible
banner (snoozed 7 days on dismiss); on iOS Safari (no install event) it shows
"Add to Home Screen" guidance instead. `InstallButton` is a reusable trigger
(used in Settings). Installed state is detected via `display-mode: standalone`
(and `navigator.standalone` on iOS) and hides the prompts.

---

## 7. Security

- CSP + `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`,
  `Permissions-Policy`, `Strict-Transport-Security` (`next.config.ts`).
- `connect-src` is derived from `NEXT_PUBLIC_API_BASE_URL` so the SPA can reach
  the API; dev additionally allows `ws:` for HMR.
- The service worker never caches cross-origin/API responses or any non-GET
  request, so tokens and private data are never persisted.
- Auth remains cookie/session based and unchanged.

> CSP note: Next injects inline bootstrap scripts and Tailwind emits inline
> styles, so `script-src`/`style-src` include `'unsafe-inline'`. Moving to a
> nonce-based CSP would require a custom Next middleware and is the only known
> deviation from a "no `unsafe-inline`" ideal.

---

## 8. Testing & verification

- **Build:** `npm run build` (emits `/manifest.webmanifest`, `/offline`).
- **Lighthouse:** run against a production build (`npm run build && npm start`)
  over HTTPS or `localhost`. Installability, offline, and PWA checks should pass.
- **Manual offline:** DevTools → Application → Service Workers → **Offline**, then
  navigate — previously visited pages load from cache; unknown routes show
  `/offline`.
- **Update:** bump `VERSION` in `sw.js`, rebuild, reload — the update banner
  appears.
- **Outbox:** go offline, perform an `offlineQueue` action, confirm an entry in
  Application → IndexedDB → `hostel-pwa` → `outbox`, then go online and watch it
  drain.

---

## 9. Browser-imposed limitations

- **Background Sync**: Chromium only. Safari/Firefox fall back to `online`-event
  flushing.
- **Web Push on iOS**: requires iOS 16.4+ **and** the app installed to the Home
  Screen.
- **`beforeinstallprompt`**: not fired by Safari/Firefox — install is manual
  (the UI adapts).
- **`display_override: window-controls-overlay`**: desktop Chromium only; falls
  back to `standalone`.
