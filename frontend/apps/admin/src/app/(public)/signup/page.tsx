"use client";

import React, { useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Input } from "@hostel/ui";
import { Button } from "@hostel/ui";
import { suggestWorkspaceUsername, validateWorkspaceUsername } from "@hostel/utils";
import { authApi } from "@/features/auth/api/auth.api";
import { savePendingSignup } from "@/features/auth/lib/pendingSignup";
import { WorkspaceUsernameField } from "@/features/tenants/components/WorkspaceUsernameField";
import type { AvailabilityState } from "@/features/tenants/hooks/useWorkspaceAvailability";
import { useToast } from "@hostel/ui";

function scorePassword(pw: string) {
  // Simple strength scoring (client-side)
  let score = 0;
  if (pw.length >= 8) score++;
  if (pw.length >= 12) score++;
  if (/[A-Z]/.test(pw)) score++;
  if (/[a-z]/.test(pw)) score++;
  if (/\d/.test(pw)) score++;
  if (/[^A-Za-z0-9]/.test(pw)) score++;
  return Math.min(score, 6);
}

function strengthLabel(score: number) {
  if (score <= 2) return "Weak";
  if (score <= 4) return "Medium";
  return "Strong";
}

export default function SignupPage() {
  const router = useRouter();
  const toast = useToast();

  const [hostelName, setHostelName] = useState("");
  const [hostelPhone, setHostelPhone] = useState("");
  const [hostelAddress, setHostelAddress] = useState("");
  const [ownerName, setOwnerName] = useState("");

  // Permanent workspace username (subdomain). Auto-derived from the hostel
  // name until the user edits the field themselves.
  const [workspaceUsername, setWorkspaceUsername] = useState("");
  const [workspaceTouched, setWorkspaceTouched] = useState(false);
  const [workspaceState, setWorkspaceState] = useState<AvailabilityState | null>(null);

  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");

  const [password, setPassword] = useState("");
  const [password2, setPassword2] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [showPw2, setShowPw2] = useState(false);

  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  const pwScore = useMemo(() => scorePassword(password), [password]);

  const usernameOk = useMemo(() => {
    const u = username.trim();
    if (u.length < 3) return false;
    // letters, numbers, underscore, dot
    return /^[a-zA-Z0-9._]+$/.test(u);
  }, [username]);

  const phoneOk = useMemo(() => {
    const p = hostelPhone.trim();
    if (!p) return true; // optional
    // Nepal-ish general check: allow + and digits, 7-15 chars
    return /^[+\d][\d]{6,14}$/.test(p);
  }, [hostelPhone]);

  const emailOk = useMemo(() => {
    const e = email.trim();
    // Simple, permissive email shape; the backend does the authoritative check.
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e);
  }, [email]);

  // Step 1: validate the details, email a verification code, then hand off to
  // the OTP page. The account itself is created there once the code is entered.
  async function onContinue(e: React.FormEvent) {
    e.preventDefault();
    if (loading) return;

    setErr("");

    const cleanEmail = email.trim();
    const payload = {
      hostel_name: hostelName.trim(),
      workspace_username: workspaceUsername.trim(),
      hostel_phone: hostelPhone.trim() || "",
      hostel_address: hostelAddress.trim() || "",
      owner_name: ownerName.trim() || "",
      username: username.trim(),
      email: cleanEmail,
      password,
      password2,
    };

    // Frontend validation — surfaced inline so a disabled button never hides "why".
    if (!payload.hostel_name) return setErr("Hostel name is required.");
    if (!payload.workspace_username) return setErr("Workspace username is required.");
    {
      const check = validateWorkspaceUsername(payload.workspace_username);
      if (!check.ok) return setErr(`Workspace username: ${check.message}`);
    }
    if (workspaceState?.status === "taken") {
      return setErr("That workspace username is already taken — pick another or use a suggestion.");
    }
    if (!payload.username) return setErr("Username is required.");
    if (!usernameOk) return setErr("Username must be 3+ chars and only a-z, 0-9, dot, underscore.");
    if (!cleanEmail) return setErr("Email is required.");
    if (!emailOk) return setErr("Enter a valid email address.");
    if (!phoneOk) return setErr("Phone looks invalid. Use digits only (optionally +).");
    if (!password) return setErr("Password is required.");
    if (password.length < 8) return setErr("Password should be at least 8 characters.");
    if (password !== password2) return setErr("Passwords do not match.");

    setLoading(true);
    try {
      await authApi.requestSignupOtp({ email: cleanEmail });
      savePendingSignup(payload);
      toast.success(
        `We sent a 6-digit verification code to ${cleanEmail}. Check your inbox (and spam).`,
        "Verify your email",
      );
      router.push("/verify-otp");
    } catch (e: any) {
      const msg = e?.message || "Could not send the verification code. Try again.";
      setErr(msg);
      toast.error(msg, "Couldn't send code");
    } finally {
      setLoading(false);
    }
  }

  function resetForm() {
    setHostelName("");
    setWorkspaceUsername("");
    setWorkspaceTouched(false);
    setWorkspaceState(null);
    setHostelPhone("");
    setHostelAddress("");
    setOwnerName("");
    setUsername("");
    setEmail("");
    setPassword("");
    setPassword2("");
    setErr("");
  }

  return (
    <main className="min-h-screen grid place-items-center p-6 bg-gray-50">
      <form
        onSubmit={onContinue}
        className="max-w-md w-full bg-white border rounded-2xl p-6 shadow-sm"
      >
        <h1 className="text-2xl font-bold mb-1">Create Hostel</h1>
        <p className="text-gray-600 mb-6">
          Creates hostel + owner account and gives you a Hostel ID.
        </p>

        <div className="space-y-3">
          <Input
            id="hostel_name"
            name="hostel_name"
            label="Hostel Name"
            value={hostelName}
            onChange={(e) => {
              const value = e.target.value;
              if (value.length <= 15) {
                setHostelName(value);
                // Keep the workspace username in sync with the hostel name
                // until the user takes over the field themselves.
                if (!workspaceTouched) setWorkspaceUsername(suggestWorkspaceUsername(value));
              }
            }}
            required
            autoComplete="organization"
          />

          <WorkspaceUsernameField
            value={workspaceUsername}
            onChange={(value) => {
              setWorkspaceTouched(true);
              setWorkspaceUsername(value);
            }}
            onStateChange={setWorkspaceState}
            disabled={loading}
          />

          <Input
            id="hostel_phone"
            name="hostel_phone"
            label="Hostel Phone (optional)"
            value={hostelPhone}
            onChange={(e) => {
              const value = e.target.value;
              if (value.length <= 12) setHostelPhone(value);
            }}
            autoComplete="tel"
          />
          {!phoneOk && (
            <div className="text-xs text-red-600">
              Phone format looks wrong (digits only, optionally +).
            </div>
          )}

          <Input
            id="hostel_address"
            name="hostel_address"
            label="Hostel Address (optional)"
            value={hostelAddress}
            onChange={(e) => {
              const value = e.target.value;
              if (value.length <= 30) setHostelAddress(value);
            }}
            autoComplete="street-address"
          />

          <Input
            id="owner_name"
            name="owner_name"
            label="Owner Name (optional)"
            value={ownerName}
            onChange={(e) => {
              const value = e.target.value;
              if (value.length <= 15) setOwnerName(value);
            }}
            autoComplete="name"
          />

          <hr className="my-2" />

          <Input
            id="username"
            name="username"
            label="Username"
            value={username}
            onChange={(e) => {
              const value = e.target.value;
              if (value.length <= 30) setUsername(value);
            }}
            required
            autoComplete="username"
          />
          {!usernameOk && username.trim().length > 0 && (
            <div className="text-xs text-red-600">
              Use 3+ chars. Allowed: letters, numbers, dot, underscore.
            </div>
          )}

          <Input
            id="email"
            name="email"
            label="Email"
            type="email"
            value={email}
            onChange={(e) => {
              const value = e.target.value;
              if (value.length <= 30) setEmail(value);
            }}
            required
            autoComplete="email"
          />
          {email.trim().length > 0 && !emailOk && (
            <div className="text-xs text-red-600">Enter a valid email address.</div>
          )}
          <div className="text-xs text-gray-500">
            We&apos;ll email a 6-digit code to verify this address in the next step.
          </div>

          <div className="flex gap-2 items-end">
            <div className="flex-1">
              <Input
                id="password"
                name="password"
                label="Password"
                type={showPw ? "text" : "password"}
                value={password}
                onChange={(e) => {
                  const value = e.target.value;
                  if (value.length <= 15) setPassword(value);
                }}
                required
                autoComplete="new-password"
              />
            </div>
            <Button type="button" onClick={() => setShowPw((s) => !s)}>
              {showPw ? "Hide" : "Show"}
            </Button>
          </div>

          <div className="text-xs text-gray-600">
            Strength: <span className="font-semibold">{strengthLabel(pwScore)}</span>{" "}
            <span className="text-gray-400">(min 8 chars recommended)</span>
          </div>

          <div className="flex gap-2 items-end">
            <div className="flex-1">
              <Input
                id="password2"
                name="password2"
                label="Confirm Password"
                type={showPw2 ? "text" : "password"}
                value={password2}
                onChange={(e) => {
                  const value = e.target.value;
                  if (value.length <= 15) setPassword2(value);
                }}
                required
                autoComplete="new-password"
              />
            </div>
            <Button type="button" onClick={() => setShowPw2((s) => !s)}>
              {showPw2 ? "Hide" : "Show"}
            </Button>
          </div>
        </div>

        {err && <div className="mt-3 text-sm text-red-600">{err}</div>}

        <div className="mt-5 flex gap-2">
          <Button type="submit" className="w-full" loading={loading}>
            {loading ? "Sending code..." : "Continue"}
          </Button>
          <Button type="button" onClick={resetForm} disabled={loading}>
            Reset
          </Button>
        </div>

        <div className="mt-4 text-center text-sm">
          <span className="text-gray-600">Already have an account?</span>
          <Link href="/login" className="ml-1 font-semibold text-blue-600 hover:underline">
            Login
          </Link>
        </div>
      </form>
    </main>
  );
}
