"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@hostel/api";
import { authStore } from "./auth.store";
import { hostelStore } from "@hostel/utils";
import { AUTH_UNAUTHORIZED } from "./events";
import { clearUserContext, setUserContext } from "@hostel/utils";

export type AuthUser = {
  id: number;
  username: string;
  email?: string;
  first_name?: string;
  last_name?: string;
  role?: string;
  is_staff?: boolean;
  is_active?: boolean;
  date_joined?: string;
  last_login?: string | null;
  hostel_code?: string | null;
  hostel_id?: string | null;
  /** When true, the account was provisioned with a temporary/default password
   * and must set a new one before using the app (first-login gate). */
  must_change_password?: boolean;
};

export type AuthStatus = "loading" | "authenticated" | "unauthenticated";

type AuthContextValue = {
  status: AuthStatus;
  user: AuthUser | null;
  role: string | null;
  hostelCode: string | null;
  /** Re-validate the session against the backend (`/auth/me`). */
  refresh: () => Promise<void>;
  /** Mark the client authenticated after a successful login. */
  onLoggedIn: (user?: AuthUser | null, hostelCode?: string) => void;
  /** Log out: revoke server session, clear local state, go to /login. */
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

const SESSION_KEY = "session_active"; // mirrors auth.store.ts

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [user, setUser] = useState<AuthUser | null>(null);
  // Guards against concurrent /auth/me calls and double redirects.
  const validating = useRef(false);

  const applyUser = useCallback((u: AuthUser | null) => {
    setUser(u);
    if (u) {
      setUserContext({ id: u.id, role: u.role ?? null, hostel: hostelStore.getCode() ?? null });
    } else {
      clearUserContext();
    }
  }, []);

  const refresh = useCallback(async () => {
    if (validating.current) return;
    // No local session marker -> definitively logged out; skip the network call.
    if (!authStore.getAccess()) {
      applyUser(null);
      setStatus("unauthenticated");
      return;
    }
    validating.current = true;
    try {
      const me = await apiFetch<AuthUser>("/auth/me/", { method: "GET", auth: false });
      applyUser(me);
      if (me?.role) {
        try {
          localStorage.setItem("role", me.role);
        } catch {}
      }
      setStatus("authenticated");
    } catch {
      // Session invalid/expired (api client already attempted a refresh).
      authStore.clear();
      applyUser(null);
      setStatus("unauthenticated");
    } finally {
      validating.current = false;
    }
  }, [applyUser]);

  const onLoggedIn = useCallback(
    (u?: AuthUser | null, hostelCode?: string) => {
      authStore.setAuthed();
      if (hostelCode) {
        authStore.setHostelCode(hostelCode);
        hostelStore.set({ code: hostelCode });
      }
      if (u) {
        applyUser(u);
        setStatus("authenticated");
      } else {
        void refresh();
      }
    },
    [applyUser, refresh]
  );

  const logout = useCallback(async () => {
    try {
      await apiFetch("/auth/logout/", { method: "POST", auth: false });
    } catch {
      // Even if the server call fails, we still clear locally.
    }
    authStore.clear();
    hostelStore.clear();
    try {
      localStorage.removeItem("role");
    } catch {}
    applyUser(null);
    setStatus("unauthenticated");
    router.replace("/login");
  }, [applyUser, router]);

  // Initial validation on mount.
  useEffect(() => {
    void refresh();
  }, [refresh]);

  // Global 401 (refresh failed) from the API client -> drop the client session.
  // We intentionally do NOT redirect here: public pages (landing, marketing,
  // login/signup) must stay put even if a background call 401s. The (protected)
  // layout is the single place that redirects to /login when it observes
  // status become "unauthenticated", so only authenticated routes bounce.
  useEffect(() => {
    function onUnauthorized() {
      authStore.clear();
      applyUser(null);
      setStatus("unauthenticated");
    }
    window.addEventListener(AUTH_UNAUTHORIZED, onUnauthorized);
    return () => window.removeEventListener(AUTH_UNAUTHORIZED, onUnauthorized);
  }, [applyUser]);

  // Cross-tab sync: react when the session marker changes in another tab.
  useEffect(() => {
    function onStorage(e: StorageEvent) {
      if (e.key !== SESSION_KEY) return;
      if (e.newValue === null) {
        // Logged out elsewhere. Update state only; the (protected) layout will
        // redirect if the current route needs auth — public pages stay put.
        applyUser(null);
        setStatus("unauthenticated");
      } else {
        // Logged in elsewhere -> pick up the new session.
        void refresh();
      }
    }
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, [applyUser, refresh]);

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      user,
      role: user?.role ?? null,
      hostelCode: typeof window !== "undefined" ? authStore.getHostelCode() : null,
      refresh,
      onLoggedIn,
      logout,
    }),
    [status, user, refresh, onLoggedIn, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an <AuthProvider>.");
  return ctx;
}
