/**
 * At-rest encryption for the offline outbox.
 *
 * Queued mutations can contain PII (student details, payment amounts, ID
 * numbers) and sit in IndexedDB until connectivity returns — potentially on a
 * shared or lost device. We encrypt the request *body* with AES-GCM before it
 * is persisted.
 *
 * The key is a 256-bit AES-GCM key generated with `extractable: false`, so it
 * lives only as an opaque CryptoKey inside IndexedDB and can never be read out
 * as raw bytes by script (an XSS can ask the browser to decrypt, but cannot
 * steal the key to decrypt offline elsewhere). The same key record is read by
 * the service worker (public/sw.js) when it replays the queue — see
 * `decryptOutboxBody` there. The app is the only writer; the SW only reads.
 */
import { kvGet, kvSet } from "./db";

export const OUTBOX_KEY_ID = "__outbox_crypto_key__";

export type EncryptedBlob = { iv: number[]; data: ArrayBuffer };

function subtle(): SubtleCrypto | null {
  return typeof crypto !== "undefined" && crypto.subtle ? crypto.subtle : null;
}

/** Get (or lazily create + persist) the non-extractable outbox key. */
export async function getOutboxKey(): Promise<CryptoKey | null> {
  if (!subtle()) return null;
  try {
    const existing = await kvGet<CryptoKey>(OUTBOX_KEY_ID);
    if (existing) return existing;
    const key = await subtle()!.generateKey({ name: "AES-GCM", length: 256 }, false, [
      "encrypt",
      "decrypt",
    ]);
    await kvSet(OUTBOX_KEY_ID, key);
    return key;
  } catch {
    return null;
  }
}

/** Encrypt a UTF-8 string. Returns null if WebCrypto is unavailable. */
export async function encryptString(plaintext: string): Promise<EncryptedBlob | null> {
  const s = subtle();
  const key = await getOutboxKey();
  if (!s || !key) return null;
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const data = await s.encrypt({ name: "AES-GCM", iv }, key, new TextEncoder().encode(plaintext));
  return { iv: Array.from(iv), data };
}

/** Decrypt a blob produced by encryptString. Throws if the key/data is bad. */
export async function decryptString(blob: EncryptedBlob): Promise<string> {
  const s = subtle();
  const key = await getOutboxKey();
  if (!s || !key) throw new Error("crypto unavailable");
  const buf = await s.decrypt({ name: "AES-GCM", iv: new Uint8Array(blob.iv) }, key, blob.data);
  return new TextDecoder().decode(buf);
}
