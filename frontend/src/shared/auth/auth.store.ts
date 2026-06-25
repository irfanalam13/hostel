import { storage } from "@/shared/lib/storage";

// Auth is cookie-native: the access/refresh JWTs live in httpOnly cookies set
// by the backend and are NOT readable from JS. We persist only a non-sensitive
// "there is a session" marker so the client-side route guards know whether to
// attempt protected pages. The cookies are what actually authenticate requests.
const SESSION_KEY = "session_active";
const HOSTEL_CODE_KEY = "hostel_code";

export const authStore = {
  // Truthy when a session marker exists. Kept named getAccess() so the existing
  // route guards keep working unchanged.
  getAccess() {
    return storage.get(SESSION_KEY);
  },
  getRefresh() {
    // Refresh token is an httpOnly cookie; nothing to read here.
    return null;
  },
  getHostelCode() {
    return storage.get(HOSTEL_CODE_KEY);
  },
  setAuthed() {
    storage.set(SESSION_KEY, "1");
  },
  // Back-compat shim: callers used to stash JWTs here. Tokens now live in
  // cookies, so we ignore the args and just mark the session active.
  setTokens(_access?: string, _refresh?: string) {
    storage.set(SESSION_KEY, "1");
  },
  setHostelCode(code: string) {
    storage.set(HOSTEL_CODE_KEY, code);
  },
  clear() {
    storage.remove(SESSION_KEY);
    storage.remove(HOSTEL_CODE_KEY);
    // Sweep any legacy token keys left over from the old Bearer flow.
    storage.remove("access_token");
    storage.remove("refresh_token");
    storage.remove("hostel_access");
    storage.remove("hostel_refresh");
  },
};
