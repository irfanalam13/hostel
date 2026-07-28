"use client";

import React, { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Button, Input, useToast } from "@hostel/ui";
import { authStore, useAuth } from "@hostel/auth";
import { hostelStore } from "@hostel/utils";
import { authApi, type SuperAdminLoginResponse } from "../api/auth.api";

/**
 * Platform super-admin login — a distinct axis from tenant login
 * (WorkspaceLoginForm): no Hostel ID, no workspace branding, no portal.
 * Reached only via the dedicated admin.<TENANT_BASE_DOMAIN> host (see
 * securityProxy.ts) or directly at /super-admin-login.
 * See docs/AUTHENTICATION.md "Super-admin access".
 */
export function SuperAdminLoginForm() {
  const router = useRouter();
  const toast = useToast();
  const { onLoggedIn } = useAuth();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(false);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  // See WorkspaceLoginForm.tsx for why this guard is a ref, not the `loading`
  // state: state only takes effect on the next render, so a near-simultaneous
  // second submit (Enter + click) can still read `loading === false`.
  const submittingRef = useRef(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (submittingRef.current) return;
    setErr("");

    if (!username.trim()) return setErr("Username or email is required.");
    if (!password) return setErr("Password is required.");

    submittingRef.current = true;
    setLoading(true);
    try {
      const data: SuperAdminLoginResponse = await authApi.superAdminLogin({
        username: username.trim(),
        password,
        remember,
      });

      if (data?.hostel_code) {
        authStore.setHostelCode(data.hostel_code);
        hostelStore.set({ code: data.hostel_code });
      }
      onLoggedIn((data?.user as never) ?? null, data?.hostel_code ?? undefined);

      toast.success("Welcome back.", "Login successful");
      router.replace(data?.redirect || "/platform");
    } catch (e: unknown) {
      const anyErr = e as { data?: { detail?: string }; message?: string };
      const msg = anyErr?.data?.detail || anyErr?.message || "Something went wrong";
      setErr(msg);
      toast.error(msg, "Login failed");
    } finally {
      submittingRef.current = false;
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-[var(--background)] p-4">
      <div className="w-full max-w-sm space-y-6 rounded-[20px] border border-[var(--border)] bg-[var(--card)] p-6">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-wide text-[var(--accent)]">
            Platform · Super Admin
          </div>
          <h1 className="mt-1 text-xl font-semibold text-[var(--foreground)]">Sign in</h1>
          <p className="mt-0.5 text-sm text-[var(--muted)]">
            Platform operator access only — not a hostel account.
          </p>
        </div>

        <form onSubmit={onSubmit} className="space-y-3">
          <Input
            label="Username or email"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            autoFocus
          />
          <Input
            label="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
          />
          <label className="flex items-center gap-2 text-sm text-[var(--foreground-secondary)]">
            <input
              type="checkbox"
              checked={remember}
              onChange={(e) => setRemember(e.target.checked)}
              className="h-4 w-4"
            />
            Remember me
          </label>

          {err ? <div className="text-sm text-[var(--error)]">{err}</div> : null}

          <Button type="submit" loading={loading} className="w-full">
            Sign in
          </Button>
        </form>
      </div>
    </main>
  );
}
