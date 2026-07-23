/**
 * Web Push subscription manager (frontend half).
 *
 * Requires a VAPID public key in NEXT_PUBLIC_VAPID_PUBLIC_KEY and a backend that
 * implements the subscription endpoints (see Documentation/PWA.md → Push):
 *   POST /api/push/subscribe/    { subscription, user_agent }
 *   POST /api/push/unsubscribe/  { endpoint }
 *
 * If the key is absent or the browser doesn't support Push, every call degrades
 * gracefully (returns a status object instead of throwing) so the rest of the
 * PWA keeps working.
 */
import { api } from "@hostel/api";

const VAPID_PUBLIC_KEY = process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY?.trim() || "";

export type PushPermission = "default" | "granted" | "denied" | "unsupported";

export function pushSupported(): boolean {
  return (
    typeof window !== "undefined" &&
    "serviceWorker" in navigator &&
    "PushManager" in window &&
    "Notification" in window
  );
}

export function pushConfigured(): boolean {
  return pushSupported() && VAPID_PUBLIC_KEY.length > 0;
}

export function permissionState(): PushPermission {
  if (!pushSupported()) return "unsupported";
  return Notification.permission as PushPermission;
}

function urlBase64ToUint8Array(base64String: string): BufferSource {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(base64);
  const buffer = new ArrayBuffer(raw.length);
  const output = new Uint8Array(buffer);
  for (let i = 0; i < raw.length; i++) output[i] = raw.charCodeAt(i);
  return output;
}

/** Returns the current push subscription, if the user already subscribed. */
export async function getSubscription(): Promise<PushSubscription | null> {
  if (!pushSupported()) return null;
  const reg = await navigator.serviceWorker.ready;
  return reg.pushManager.getSubscription();
}

/**
 * Request permission (if needed), subscribe, and register the subscription with
 * the backend. Returns the subscription or null if the user declined / it isn't
 * configured.
 */
export async function subscribeToPush(): Promise<PushSubscription | null> {
  if (!pushConfigured()) return null;

  const permission = await Notification.requestPermission();
  if (permission !== "granted") return null;

  const reg = await navigator.serviceWorker.ready;
  let sub = await reg.pushManager.getSubscription();
  if (!sub) {
    sub = await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(VAPID_PUBLIC_KEY),
    });
  }

  await api.post("/push/subscribe/", {
    subscription: sub.toJSON(),
    user_agent: navigator.userAgent,
  });
  return sub;
}

/** Unsubscribe locally and tell the backend to forget the subscription. */
export async function unsubscribeFromPush(): Promise<boolean> {
  const sub = await getSubscription();
  if (!sub) return false;
  try {
    await api.post("/push/unsubscribe/", { endpoint: sub.endpoint });
  } catch {
    /* best effort — still unsubscribe locally */
  }
  return sub.unsubscribe();
}
