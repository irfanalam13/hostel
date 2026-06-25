// src/shared/lib/storage.ts

function isBrowser() {
  return typeof window !== "undefined";
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