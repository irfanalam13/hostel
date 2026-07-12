/**
 * Service-worker registration + safe update lifecycle.
 *
 * Update flow:
 *   1. A new SW is found → it installs and enters the "waiting" state.
 *   2. We surface "update available" to the UI (UpdateBanner).
 *   3. User clicks "Update now" → applyUpdate() posts SKIP_WAITING.
 *   4. The new SW activates → "controllerchange" fires → we reload once.
 *
 * `onUpdate` may also be triggered for a *critical/forced* update if the SW
 * decides to skip waiting itself; the reload-on-controllerchange guard handles
 * both paths without an infinite reload loop.
 */

export type RegisterCallbacks = {
  onReady?: (reg: ServiceWorkerRegistration) => void;
  onUpdateAvailable?: (reg: ServiceWorkerRegistration) => void;
  onMessage?: (data: unknown) => void;
};

let waitingWorker: ServiceWorker | null = null;
let reloading = false;

export function isPwaSupported(): boolean {
  return typeof navigator !== "undefined" && "serviceWorker" in navigator;
}

export function isStandalone(): boolean {
  if (typeof window === "undefined") return false;
  return (
    window.matchMedia?.("(display-mode: standalone)").matches ||
    // iOS Safari
    (window.navigator as unknown as { standalone?: boolean }).standalone === true
  );
}

/**
 * Tear down any service worker (and its caches) currently controlling this
 * origin. Used by dev cleanup and available to callers that need a hard reset.
 */
export async function unregisterServiceWorker(): Promise<void> {
  if (!isPwaSupported()) return;
  try {
    const regs = await navigator.serviceWorker.getRegistrations();
    await Promise.all(regs.map((reg) => reg.unregister()));
    if (typeof caches !== "undefined") {
      const keys = await caches.keys();
      await Promise.all(keys.map((key) => caches.delete(key)));
    }
  } catch {
    /* best-effort cleanup — never throw during app bootstrap */
  }
}

export function registerServiceWorker(cb: RegisterCallbacks = {}): void {
  if (!isPwaSupported()) return;

  // A production caching SW must NEVER control the dev server. It serves build
  // output cache-first — safe in prod where /_next/static chunks are content-
  // hashed and immutable, but Turbopack/HMR rebuild chunk URLs constantly in
  // dev. The worker then hands back stale JS: the network-first HTML shell
  // still renders, but the page never hydrates, so it looks "stuck rendering"
  // (forms fall back to native GET submits, soft navigations fail with a red
  // X). Existing dev installs self-heal because we actively unregister here.
  if (process.env.NODE_ENV !== "production") {
    void unregisterServiceWorker();
    return;
  }

  // Reload exactly once when a *new* worker takes over from an existing one
  // (a genuine update). The very first SW to claim a previously-uncontrolled
  // page is NOT an update — the assets it now serves are the ones already
  // loaded — so reloading there just causes a needless flash on first visit
  // (and races anything inspecting the page right after control is gained).
  let hadController = navigator.serviceWorker.controller !== null;
  navigator.serviceWorker.addEventListener("controllerchange", () => {
    if (!hadController) {
      hadController = true; // first claim on a fresh page — no reload needed
      return;
    }
    if (reloading) return;
    reloading = true;
    window.location.reload();
  });

  navigator.serviceWorker.addEventListener("message", (event) => {
    cb.onMessage?.(event.data);
  });

  const onLoad = () => {
    navigator.serviceWorker
      .register("/sw.js", { scope: "/" })
      .then((reg) => {
        cb.onReady?.(reg);

        // Already waiting (installed before this page load).
        if (reg.waiting && navigator.serviceWorker.controller) {
          waitingWorker = reg.waiting;
          cb.onUpdateAvailable?.(reg);
        }

        reg.addEventListener("updatefound", () => {
          const installing = reg.installing;
          if (!installing) return;
          installing.addEventListener("statechange", () => {
            if (installing.state === "installed" && navigator.serviceWorker.controller) {
              // A previous SW controls the page → this is an update, not first install.
              waitingWorker = reg.waiting ?? installing;
              cb.onUpdateAvailable?.(reg);
            }
          });
        });

        // Periodically check for updates (e.g. long-lived installed app).
        setInterval(() => reg.update().catch(() => {}), 60 * 60 * 1000);
      })
      .catch((err) => console.error("[PWA] SW registration failed", err));
  };

  if (document.readyState === "complete") onLoad();
  else window.addEventListener("load", onLoad, { once: true });
}

/**
 * Ask the active service worker for its version (the SW replies to GET_VERSION
 * over a MessageChannel). The SW's cache names are derived from this same
 * version string, so it doubles as the cache version. Resolves null if there's
 * no controlling worker or it doesn't answer in time.
 */
export function getServiceWorkerVersion(timeoutMs = 2000): Promise<string | null> {
  const controller = isPwaSupported() ? navigator.serviceWorker.controller : null;
  if (!controller) return Promise.resolve(null);
  return new Promise((resolve) => {
    const channel = new MessageChannel();
    const timer = setTimeout(() => resolve(null), timeoutMs);
    channel.port1.onmessage = (event) => {
      clearTimeout(timer);
      resolve((event.data as { version?: string })?.version ?? null);
    };
    controller.postMessage({ type: "GET_VERSION" }, [channel.port2]);
  });
}

/** Tell the waiting worker to activate; the reload happens on controllerchange. */
export function applyUpdate(): void {
  const worker = waitingWorker;
  if (!worker) {
    window.location.reload();
    return;
  }
  worker.postMessage({ type: "SKIP_WAITING" });
}
