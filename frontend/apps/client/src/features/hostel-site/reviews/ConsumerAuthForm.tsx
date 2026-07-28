"use client";

import React, { useState } from "react";
import { DiscoveryApiError } from "@/features/discovery/discoveryFetch";
import { consumerLogin, consumerSignup, requestSignupOtp } from "./reviewsApi";

/**
 * `/api/auth/*` responses are deliberately left un-enveloped by the backend
 * (the auth handshake namespace stays raw — see
 * `apps.common.renderers.StandardJSONRenderer._should_wrap`), so
 * `DiscoveryApiError.message` falls back to a generic string for these calls;
 * the real DRF field errors (e.g. `{"email": ["already exists"]}`) still land
 * in `.fieldErrors`. Pull the first one out for a message worth showing.
 */
function authErrorMessage(err: unknown): string {
  if (err instanceof DiscoveryApiError) {
    const fields = err.fieldErrors;
    if (fields && typeof fields === "object") {
      const first = Object.values(fields as Record<string, unknown>)[0];
      if (Array.isArray(first) && first.length) return String(first[0]);
      if (typeof first === "string") return first;
    }
    return err.message;
  }
  return err instanceof Error ? err.message : "Something went wrong.";
}

const inputClass =
  "w-full rounded-[var(--site-radius)] border border-gray-300 bg-white px-3 py-2 text-sm " +
  "focus:outline-none focus:ring-2 focus:ring-[var(--site-primary)]";

/** Inline consumer signup/login, used by `WriteReviewCTA` for an anonymous
 * visitor — never a redirect to the staff `/login`, since a reviewer account
 * is a separate, lightweight CONSUMER role. */
export function ConsumerAuthForm({ onDone }: { onDone: () => void }) {
  const [mode, setMode] = useState<"signup" | "login">("signup");
  const [otpSent, setOtpSent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    full_name: "", phone: "", email: "", otp: "", password: "", password2: "",
  });

  function set(field: keyof typeof form) {
    return (e: React.ChangeEvent<HTMLInputElement>) => setForm((f) => ({ ...f, [field]: e.target.value }));
  }

  async function sendOtp() {
    if (!form.email) {
      setError("Enter your email first.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await requestSignupOtp(form.email);
      setOtpSent(true);
    } catch (err) {
      setError(authErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      if (mode === "signup") {
        if (form.password !== form.password2) throw new Error("Passwords do not match.");
        await consumerSignup(form);
      } else {
        await consumerLogin({ email: form.email, password: form.password });
      }
      onDone();
    } catch (err) {
      setError(authErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="rounded-2xl border border-gray-200 p-5">
      <div className="mb-4 flex gap-2 text-sm font-medium">
        <button
          type="button"
          onClick={() => setMode("signup")}
          className={mode === "signup" ? "text-[var(--site-primary)]" : "text-gray-400"}
        >
          Sign up
        </button>
        <span className="text-gray-300">·</span>
        <button
          type="button"
          onClick={() => setMode("login")}
          className={mode === "login" ? "text-[var(--site-primary)]" : "text-gray-400"}
        >
          Log in
        </button>
      </div>

      <form onSubmit={onSubmit} className="space-y-3">
        {mode === "signup" && (
          <>
            <input required placeholder="Your name" value={form.full_name} onChange={set("full_name")} className={inputClass} maxLength={255} />
            <input required placeholder="Phone number" value={form.phone} onChange={set("phone")} className={inputClass} maxLength={30} />
          </>
        )}
        <input required type="email" placeholder="Email" value={form.email} onChange={set("email")} className={inputClass} maxLength={120} />
        {mode === "signup" && (
          <div className="flex gap-2">
            <input
              required
              placeholder="Verification code"
              value={form.otp}
              onChange={set("otp")}
              className={inputClass}
              maxLength={6}
            />
            <button
              type="button"
              onClick={sendOtp}
              disabled={busy}
              className="shrink-0 whitespace-nowrap rounded-[var(--site-radius)] border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-60"
            >
              {otpSent ? "Resend code" : "Send code"}
            </button>
          </div>
        )}
        <input required type="password" placeholder="Password" value={form.password} onChange={set("password")} className={inputClass} minLength={8} />
        {mode === "signup" && (
          <input required type="password" placeholder="Confirm password" value={form.password2} onChange={set("password2")} className={inputClass} minLength={8} />
        )}
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button
          type="submit"
          disabled={busy}
          className="w-full rounded-[var(--site-radius)] bg-[var(--site-primary)] px-5 py-2.5 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-60"
        >
          {busy ? "Please wait…" : mode === "signup" ? "Create account" : "Log in"}
        </button>
      </form>
    </div>
  );
}
