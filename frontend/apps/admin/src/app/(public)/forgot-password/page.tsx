"use client";

import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { authApi } from "@/features/auth/api/auth.api";
import { Button } from "@hostel/ui";
import { Input } from "@hostel/ui";
import { useToast } from "@hostel/ui";

export default function ForgotPasswordPage() {
  const router = useRouter();
  const toast = useToast();
  const [identifier, setIdentifier] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (loading) return;
    setLoading(true);
    try {
      const payload = identifier.includes("@") ? { email: identifier } : { username: identifier };
      const res = await authApi.forgotPassword(payload);
      setMessage(res.detail);
      toast.success(res.detail, "Check your email");
      // Redirect after 2 seconds so they can read the success message
      setTimeout(() => {
        router.push(`/reset-password?email_or_username=${encodeURIComponent(identifier)}`);
      }, 2000);
    } catch (err: any) {
      const msg = err?.message || "Failed to request password reset.";
      setMessage(msg);
      toast.error(msg, "Request failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-zinc-50 p-6">
      <form onSubmit={submit} className="mx-auto mt-16 max-w-md rounded-2xl border bg-white p-6 shadow-sm">
        <h1 className="mb-1 text-2xl font-semibold">Reset Password</h1>
        <p className="mb-4 text-sm text-zinc-500">Enter your username or email.</p>
        <Input value={identifier} onChange={(e) => setIdentifier(e.target.value)} placeholder="Username or email" required />
        <Button className="mt-4 w-full" type="submit" loading={loading}>
          {loading ? "Sending..." : "Continue"}
        </Button>
        {message ? <div className="mt-4 text-sm text-zinc-700 bg-zinc-100 p-3 rounded-lg">{message}</div> : null}
        <Link className="mt-4 block text-sm text-zinc-500 hover:text-zinc-900" href="/login">
          Back to login
        </Link>
      </form>
    </main>
  );
}
