import { authStore } from "@/shared/auth/auth.store";
import { hostelStore } from "@/shared/lib/hostel";

export type Tokens = { access: string; refresh: string };

export const tokenStore = {
  get(): string | null {
    return authStore.getAccess();
  },
  set(tokenOrTokens: string | Tokens) {
    if (typeof tokenOrTokens === "string") {
      const refresh = authStore.getRefresh() || "";
      authStore.setTokens(tokenOrTokens, refresh);
      return;
    }
    authStore.setTokens(tokenOrTokens.access, tokenOrTokens.refresh);
  },
  setTokens(access: string, refresh: string) {
    authStore.setTokens(access, refresh);
  },
  clear() {
    authStore.clear();
  },
};

const ROLE_KEY = "role";

export function getRole() {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(ROLE_KEY);
}

export function isAuthed() {
  const access = authStore.getAccess();
  const code = authStore.getHostelCode();
  return Boolean(access && code);
}

export function logoutBasic() {
  authStore.clear();
  hostelStore.clear();
  if (typeof window !== "undefined") localStorage.removeItem(ROLE_KEY);
}
