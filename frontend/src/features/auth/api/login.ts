import { apiFetch } from "@/shared/api/apiClient";
import { authStore } from "@/shared/auth/auth.store";
import type { Tokens } from "@/shared/lib/auth";

export async function login(username: string, password: string) {
  const tokens = await apiFetch<Tokens>("/auth/token/", {
    method: "POST",
    auth: false,
    body: JSON.stringify({ username, password }),
  });

  authStore.setTokens(tokens.access, tokens.refresh);
  return tokens;
}
