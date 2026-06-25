"use client";

import Link from "next/link";
import { useState } from "react";
import { authApi } from "@/features/auth/api/auth.api";
import { Button } from "@/shared/ui/Button";
import { Input } from "@/shared/ui/Input";

export default function ForgotPasswordPage() {
  const [identifier, setIdentifier] = useState("");
  const [message, setMessage] = useState("");
  const [debugLink, setDebugLink] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const payload = identifier.includes("@") ? { email: identifier } : { username: identifier };
    const res = await authApi.forgotPassword(payload);
    setMessage(res.detail);
    if (res.uid && res.token) {
      setDebugLink(`/reset-password?uid=${encodeURIComponent(res.uid)}&token=${encodeURIComponent(res.token)}`);
    }
  }

  return (
    <main className="min-h-screen bg-zinc-50 p-6">
      <form onSubmit={submit} className="mx-auto mt-16 max-w-md rounded-2xl border bg-white p-6 shadow-sm">
        <h1 className="mb-1 text-2xl font-semibold">Reset Password</h1>
        <p className="mb-4 text-sm text-zinc-500">Enter your username or email.</p>
        <Input value={identifier} onChange={(e) => setIdentifier(e.target.value)} placeholder="Username or email" required />
        <Button className="mt-4 w-full" type="submit">Continue</Button>
        {message ? <div className="mt-4 text-sm text-zinc-700">{message}</div> : null}
        {debugLink ? (
          <Link className="mt-2 block text-sm text-blue-600 hover:underline" href={debugLink}>
            Open reset link
          </Link>
        ) : null}
        <Link className="mt-4 block text-sm text-zinc-500 hover:text-zinc-900" href="/login">
          Back to login
        </Link>
      </form>
    </main>
  );
}
