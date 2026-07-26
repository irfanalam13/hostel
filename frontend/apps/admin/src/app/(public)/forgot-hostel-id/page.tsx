"use client";

import Link from "next/link";
import { useState } from "react";
import { authApi } from "@/features/auth/api/auth.api";
import { Button } from "@hostel/ui";
import { Input } from "@hostel/ui";
import { useToast } from "@hostel/ui";

export default function ForgotHostelIDPage() {
  const toast = useToast();
  const [identifier, setIdentifier] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (loading) return;
    setLoading(true);
    try {
      const res = await authApi.forgotHostelID({ email_or_username: identifier });
      setMessage(res.detail);
      toast.success(res.detail, "Check your email");
    } catch (err: any) {
      const msg = err?.message || "Failed to request Hostel ID.";
      setMessage(msg);
      toast.error(msg, "Request failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-zinc-50 p-6">
      <form onSubmit={submit} className="mx-auto mt-16 max-w-md rounded-2xl border bg-white p-6 shadow-sm">
        <h1 className="mb-1 text-2xl font-semibold">Retrieve Hostel ID</h1>
        <p className="mb-4 text-sm text-zinc-500">
          Enter the username or email linked to your account. Your registered Hostel ID details will be sent to your email inbox.
        </p>
        <Input 
          value={identifier} 
          onChange={(e) => setIdentifier(e.target.value)} 
          placeholder="Username or email" 
          required 
        />
        <Button className="mt-4 w-full" type="submit" loading={loading}>
          {loading ? "Sending..." : "Request Hostel ID"}
        </Button>
        {message ? <div className="mt-4 text-sm text-zinc-700 bg-zinc-100 p-3 rounded-lg">{message}</div> : null}
        <Link className="mt-4 block text-sm text-zinc-500 hover:text-zinc-900" href="/login">
          Back to login
        </Link>
      </form>
    </main>
  );
}
