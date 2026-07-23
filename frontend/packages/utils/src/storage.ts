// src/shared/lib/storage.ts
//
// Secure-storage policy (Phase 10):
//   - Auth tokens NEVER live here. Access/refresh JWTs are httpOnly cookies set
//     by the backend and unreadable from JS, so an XSS can't exfiltrate them.
//   - localStorage holds only non-sensitive UI markers (session flag, hostel
//     code, role, drafts). `set()` actively REFUSES anything that looks like a
//     credential as a guardrail against a future regression.
//   - `clearAll()` wipes both web-storage areas on logout so nothing lingers on
//     a shared device.

function isBrowser() {
  return typeof window !== "undefined";
}

// Heuristic for "this looks like a secret" — JWTs (xxx.yyy.zzz), bearer tokens,
// and long opaque base64/hex blobs. Used to block accidental credential storage.
const SECRET_VALUE_RE =
  /^(ey[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}|Bearer\s|[A-Fa-f0-9]{64,}|[A-Za-z0-9+/]{80,}={0,2})$/;
const SECRET_KEY_RE = /(token|secret|password|jwt|refresh|bearer|api[_-]?key|private)/i;

function looksSensitive(key: string, value: string): boolean {
  return SECRET_KEY_RE.test(key) || SECRET_VALUE_RE.test(value.trim());
}

// low-level string storage
export const storage = {
  get(key: string): string | null {
    if (!isBrowser()) return null;
    try {
      return window.localStorage.getItem(key);
    } catch {
      return null;
    }
  },

  set(key: string, value: string) {
    if (!isBrowser()) return;
    // Guardrail: tokens/secrets must stay in httpOnly cookies, never here.
    if (looksSensitive(key, value)) {
      if (process.env.NODE_ENV !== "production") {
        console.error(
          `[storage] refused to persist a credential-looking value under "${key}". ` +
            `Tokens belong in httpOnly cookies, not localStorage.`
        );
      }
      return;
    }
    try {
      window.localStorage.setItem(key, value);
    } catch {
      // ignore
    }
  },

  remove(key: string) {
    if (!isBrowser()) return;
    try {
      window.localStorage.removeItem(key);
    } catch {
      // ignore
    }
  },

  /** Wipe all web storage (call on logout / shared-device sign-out). */
  clearAll() {
    if (!isBrowser()) return;
    try {
      window.localStorage.clear();
      window.sessionStorage.clear();
    } catch {
      // ignore
    }
  },
};

// ✅ what your app/store expects (typed JSON)
export function lsGet<T>(key: string, fallback: T): T {
  const raw = storage.get(key);
  if (!raw) return fallback;

  try {
    const parsed = JSON.parse(raw) as T;

    // If parsed is not an object, fallback
    if (parsed === null || typeof parsed !== "object") return fallback;

    // Merge fallback + parsed so missing fields (like payments) become default []
    return { ...(fallback as any), ...(parsed as any) } as T;
  } catch {
    return fallback;
  }
}

export function lsSet<T>(key: string, value: T) {
  try {
    storage.set(key, JSON.stringify(value));
  } catch {
    // ignore
  }
}

export function lsRemove(key: string) {
  storage.remove(key);
}

// ✅ uid helper
export function uid(prefix = "id") {
  const id =
    typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  return `${prefix}_${id}`;
}