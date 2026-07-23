import { apiFetch } from "@hostel/api";
import { authStore } from "@hostel/auth";
import type { Tokens } from "@hostel/auth";

export async function login(username: string, password: string) {
  const tokens = await apiFetch<Tokens>("/auth/token/", {
    method: "POST",
    auth: false,
    body: JSON.stringify({ username, password }),
  });

  authStore.setTokens(tokens.access, tokens.refresh);
  return tokens;
}
