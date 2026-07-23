"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Input } from "@hostel/ui";
import { Button } from "@hostel/ui";
import { authApi } from "@/features/auth/api/auth.api";
import {
  clearPendingSignup,
  loadPendingSignup,
  type PendingSignup,
} from "@/features/auth/lib/pendingSignup";
import { authStore } from "@hostel/auth";
import { hostelStore, workspaceStore } from "@hostel/utils";
import { useAuth } from "@hostel/auth";
import { useToast } from "@hostel/ui";

export default function VerifyOtpPage() {
  const router = useRouter();
  const toast = useToast();
  const { onLoggedIn } = useAuth();

  // undefined = still reading storage; null = nothing to verify (bounce away).
  const [pending, setPending] = useState<PendingSignup | null | undefined>(undefined);
  const [otp, setOtp] = useState("");
  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    const p = loadPendingSignup();
    setPending(p);
    if (!p) {
      // Landed here without a signup in progress — start over.
      router.replace("/signup");
    }
  }, [router]);

  // Step 2: supply the emailed OTP to actually create the account. On success
  // the backend sets the auth cookies, so we go straight to the dashboard.
  async function verify(code: string) {
    if (loading || !pending) return;
    if (code.length !== 6) {
      setErr("Enter the 6-digit code from your email.");
      return;
    }

    setErr("");
    setLoading(true);
    try {
      const data = await authApi.signup({ ...pending, otp: code });

      const hostelCode = data?.hostel_code || undefined;
      if (hostelCode) {
        authStore.setHostelCode(hostelCode);
        hostelStore.set({ code: hostelCode });
      }

      // Remember the freshly provisioned workspace (permanent username + URL)
      // so the app can deep-link to it later.
      const workspace = data?.workspace || undefined;
      if (workspace?.username) {
        workspaceStore.set({ slug: workspace.username, url: workspace.url });
      }

      // Auth cookies are already set by the backend; sync the client session.
      onLoggedIn(
        data?.user ? ({ ...(data.user as any), role: (data.user as any)?.role } as any) : null,
        hostelCode,
      );
      clearPendingSignup();

      const workspaceNote = workspace?.url ? ` Your workspace: ${workspace.url}` : "";
      toast.success(
        hostelCode
          ? `Account created. Your Hostel ID is ${hostelCode} — keep it safe to log in.${workspaceNote}`
          : `Your account is ready.${workspaceNote}`,
        "Welcome!",
      );
      // replace() so the back button doesn't bounce to the verification screen.
      router.replace("/dashboard");
    } catch (e: any) {
      const msg = e?.message || "Invalid or expired code. Try resending it.";
      setErr(msg);
      setOtp("");
      toast.error(msg, "Verification failed");
      setLoading(false);
    }
    // On success we navigate away, so we intentionally leave `loading` true.
  }

  async function onResend() {
    if (resending || !pending) return;
    setErr("");
    setResending(true);
    try {
      await authApi.requestSignupOtp({ email: pending.email });
      toast.success(`A new code was sent to ${pending.email}.`, "Code resent");
    } catch (e: any) {
      const msg = e?.message || "Could not resend the code. Try again.";
      setErr(msg);
      toast.error(msg, "Resend failed");
    } finally {
      setResending(false);
    }
  }

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    void verify(otp.trim());
  }

  // Reading storage / redirecting — render a quiet placeholder to avoid a flash.
  if (!pending) {
    return <main className="min-h-screen bg-gray-50 p-6" />;
  }

  return (
    <main className="min-h-screen grid place-items-center p-6 bg-gray-50">
      <form
        onSubmit={onSubmit}
        className="max-w-md w-full bg-white border rounded-2xl p-6 shadow-sm"
      >
        <h1 className="text-2xl font-bold mb-1">Verify your email</h1>
        <p className="text-gray-600 mb-6">
          Enter the 6-digit code we sent to{" "}
          <span className="font-semibold text-gray-800">{pending.email}</span>.
        </p>

        <Input
          id="otp"
          name="otp"
          label="Verification code"
          inputMode="numeric"
          autoFocus
          placeholder="123456"
          value={otp}
          onChange={(e) => {
            const value = e.target.value.replace(/\D/g, "").slice(0, 6);
            setOtp(value);
            // Auto-submit the moment all 6 digits are in.
            if (value.length === 6) void verify(value);
          }}
          required
          autoComplete="one-time-code"
        />

        {err && <div className="mt-3 text-sm text-red-600">{err}</div>}

        <Button type="submit" className="mt-5 w-full" loading={loading} disabled={otp.length !== 6}>
          {loading ? "Verifying..." : "Verify & continue"}
        </Button>

        <div className="mt-4 flex items-center justify-between text-sm">
          <button
            type="button"
            onClick={onResend}
            disabled={resending || loading}
            className="font-semibold text-blue-600 hover:underline disabled:opacity-50"
          >
            {resending ? "Resending..." : "Resend code"}
          </button>
          <Link href="/signup" className="text-gray-600 hover:underline">
            Change details
          </Link>
        </div>

        <div className="mt-6 text-xs text-gray-500 text-center">
          Didn&apos;t get it? Check your spam folder, or resend the code.
        </div>
      </form>
    </main>
  );
}
