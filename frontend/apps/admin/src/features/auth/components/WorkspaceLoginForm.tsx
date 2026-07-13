"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button, Input, useToast } from "@hostel/ui";
import { authStore, useAuth } from "@hostel/auth";
import { isWorkspaceError } from "@hostel/api";
import { hostelStore, workspaceFromLocation } from "@hostel/utils";
import { normalizeRole, postAuthHome } from "@hostel/permissions";
import { authApi, type LoginResponse, type Portal } from "../api/auth.api";
import { workspacesApi } from "@/features/tenants/api/workspaces.api";
import type { WorkspacePublicInfo } from "@/features/tenants/types/workspaces.types";
import { WorkspaceErrorScreen } from "@/features/tenants/components/WorkspaceErrorScreen";

const HOSTEL_ID_RE = /^HTL-[A-Z0-9]{8}$/;

type Props = {
  /**
   * Legacy role-portal restriction. The unified tenant login OMITS this so the
   * one page authenticates every role and the backend routes by role. Only the
   * (now redirect-only) role portals ever set it; kept for backward compat.
   */
  portal?: Portal;
  title?: string;
  subtitle?: string;
  /** Show the "create account" link (staff/admin surfaces only). */
  showSignup?: boolean;
};

function extractErrorMessage(data: unknown): string {
  if (!data) return "Login failed";
  if (typeof data === "string") return data;
  if (typeof data === "object") {
    const obj = data as Record<string, unknown>;
    if (typeof obj.detail === "string") return obj.detail;
    const first = Object.values(obj)[0];
    if (Array.isArray(first) && first.length) return String(first[0]);
    if (typeof first === "string") return first;
  }
  return "Login failed";
}

/**
 * Workspace-aware portal login (Prompt 02).
 *
 * On a workspace host (everest.myhostel.com) the tenant is resolved before
 * authentication: the page shows THAT hostel's branding (name, logo,
 * workspace username), no Hostel ID is asked for, and unknown/suspended/
 * expired workspaces render professional error screens instead of a form.
 * On the root domain the legacy Hostel-ID flow keeps working unchanged.
 *
 * The portal determines which roles may sign in (enforced server-side) and
 * where the session lands (`redirect` from the login response).
 */
export function WorkspaceLoginForm({
  portal,
  title = "Sign in",
  subtitle = "Sign in to your workspace.",
  showSignup = false,
}: Props) {
  const router = useRouter();
  const toast = useToast();
  const { onLoggedIn } = useAuth();

  // The workspace is derived from the live hostname only — it can never point
  // at a different tenant than the page the user is looking at.
  const [workspaceSlug, setWorkspaceSlug] = useState<string | null>(null);
  const [branding, setBranding] = useState<WorkspacePublicInfo | null>(null);
  const [workspaceError, setWorkspaceError] = useState<string | null>(null);

  const [hostelCode, setHostelCode] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(false);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const slug = workspaceFromLocation();
    setWorkspaceSlug(slug);
    if (!slug) {
      const saved = authStore.getHostelCode();
      if (saved) setHostelCode(saved);
      return;
    }
    // Workspace validation before the login form renders: branding on
    // success, a professional error screen when the workspace is unknown,
    // suspended, expired or disabled.
    let cancelled = false;
    workspacesApi
      .publicInfo()
      .then((info) => {
        if (!cancelled) setBranding(info);
      })
      .catch((e: unknown) => {
        if (cancelled) return;
        if (isWorkspaceError(e)) setWorkspaceError(e.code);
        // Non-workspace failures (network blip) keep the form usable — the
        // backend re-validates everything at submit anyway.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function onLogin(e: React.FormEvent) {
    e.preventDefault();
    if (loading) return;
    setErr("");

    const code = hostelCode.trim().toUpperCase();
    if (!workspaceSlug) {
      if (!code) return setErr("Hostel ID is required.");
      if (!HOSTEL_ID_RE.test(code)) return setErr("Use the official Hostel ID format: HTL-XXXXXXXX.");
    }
    if (!username.trim()) return setErr("Username or email is required.");
    if (!password) return setErr("Password is required.");

    setLoading(true);
    try {
      const data: LoginResponse = await authApi.login({
        username: username.trim(),
        password,
        // Unified login sends no portal (all roles admitted); only the legacy
        // role-portal wrappers pass one.
        ...(portal ? { portal } : {}),
        remember,
        ...(workspaceSlug ? {} : { hostel_id: code }),
      });

      const resolvedCode = data?.hostel_code || code || undefined;
      if (resolvedCode) {
        authStore.setHostelCode(resolvedCode);
        hostelStore.set({ code: resolvedCode });
      }
      onLoggedIn((data?.user as never) ?? null, resolvedCode);

      toast.success(
        branding?.name ? `Welcome back to ${branding.name}!` : "Welcome back!",
        "Login successful",
      );
      // Phase 6 — owner login. On the platform (root) domain an owner/admin may
      // belong to more than one workspace, so route through the selector, which
      // loads their organizations and auto-forwards when there is exactly one
      // (showing the picker only when there are several). A workspace-host login
      // is already bound to a single workspace, so it lands directly.
      // Otherwise the backend's role-based redirect is authoritative, falling
      // back to the client-side role map. replace() avoids a back-button bounce.
      const role = normalizeRole(data?.role);
      const mayOwnMultipleWorkspaces = role === "OWNER" || role === "ADMIN";
      if (!workspaceSlug && mayOwnMultipleWorkspaces) {
        router.replace("/select-workspace");
      } else {
        router.replace(postAuthHome(role, data?.redirect));
      }
    } catch (e: unknown) {
      if (isWorkspaceError(e)) {
        setWorkspaceError(e.code);
        return;
      }
      const anyErr = e as { data?: unknown; message?: string };
      const msg = anyErr?.data !== undefined
        ? extractErrorMessage(anyErr.data)
        : anyErr?.message || "Something went wrong";
      setErr(msg);
      toast.error(msg, "Login failed");
    } finally {
      setLoading(false);
    }
  }

  if (workspaceError) {
    return <WorkspaceErrorScreen code={workspaceError} workspace={workspaceSlug} />;
  }

  return (
    <main className="min-h-screen grid place-items-center p-6 bg-gray-50">
      <form onSubmit={onLogin} className="max-w-md w-full bg-white border rounded-2xl p-6 shadow-sm">
        {/* Workspace branding — always the resolved tenant's, never another's. */}
        {branding ? (
          <div className="mb-6 text-center">
            {branding.logo ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={branding.logo}
                alt={`${branding.name} logo`}
                className="mx-auto mb-2 h-14 w-14 rounded-xl object-contain"
              />
            ) : (
              <div className="mx-auto mb-2 grid h-14 w-14 place-items-center rounded-xl bg-blue-50 text-2xl">
                🏨
              </div>
            )}
            <div className="text-lg font-bold text-gray-900">{branding.name}</div>
            <div className="text-xs font-mono text-gray-500">
              {branding.workspace_username}
            </div>
          </div>
        ) : null}

        <h1 className="text-2xl font-bold mb-1">{title}</h1>
        <p className="text-gray-600 mb-6">{subtitle}</p>

        <div className="space-y-3">
          {!workspaceSlug && (
            <Input
              id="hostel_code"
              name="hostel_code"
              label="Hostel ID"
              value={hostelCode}
              onChange={(e) => {
                const value = e.target.value.toUpperCase().replace(/[^A-Z0-9-]/g, "");
                if (value.length <= 12) setHostelCode(value);
              }}
              placeholder="e.g. HTL-7F4D91A2"
              required
              autoComplete="off"
            />
          )}

          <Input
            id="username"
            name="username"
            label="Username or email"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            autoComplete="username"
          />

          <Input
            id="password"
            name="password"
            label="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
          />

          <label className="flex items-center gap-2 text-sm text-gray-600 select-none">
            <input
              type="checkbox"
              checked={remember}
              onChange={(e) => setRemember(e.target.checked)}
              className="h-4 w-4 rounded border-gray-300"
            />
            Keep me signed in on this device
          </label>
        </div>

        {err && <div className="mt-3 text-sm text-red-600">{err}</div>}

        <Button type="submit" className="mt-5 w-full" loading={loading}>
          {loading ? "Signing in..." : "Sign in"}
        </Button>

        {showSignup && (
          <div className="mt-4 text-center text-sm">
            <span className="text-gray-600">New hostel?</span>
            <Link href="/signup" className="ml-1 font-semibold text-blue-600 hover:underline">
              Create account
            </Link>
          </div>
        )}

        <div className="mt-2 text-center text-sm">
          <Link href="/forgot-password" className="font-semibold text-blue-600 hover:underline">
            Forgot password?
          </Link>
        </div>

        {!workspaceSlug && (
          <div className="mt-2 text-center text-sm">
            <Link href="/forgot-hostel-id" className="font-semibold text-blue-600 hover:underline">
              Forgot Hostel ID?
            </Link>
          </div>
        )}
      </form>
    </main>
  );
}





// "use client";

// import { WorkspaceLoginForm } from "@/features/auth/components/WorkspaceLoginForm";

// /** Staff portal login (alias of /login, kept for the canonical portal URL). */
// export default function StaffLoginPage() {
//   return (
//     <WorkspaceLoginForm
//       portal="staff"
//       title="Staff Login"
//       subtitle="Sign in with your staff account."
//     />
//   );
// }
