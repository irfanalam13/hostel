"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { useState } from "react";
import { authApi } from "@/features/auth/api/auth.api";
import { Button } from "@/shared/ui/Button";
import { Input } from "@/shared/ui/Input";

function ResetPasswordForm() {
  const params = useSearchParams();
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const uid = params.get("uid") || "";
  const token = params.get("token") || "";

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const res = await authApi.resetPassword({ uid, token, new_password: password });
    setMessage(res.detail);
  }

  return (
    <main className="min-h-screen bg-zinc-50 p-6">
      <form onSubmit={submit} className="mx-auto mt-16 max-w-md rounded-2xl border bg-white p-6 shadow-sm">
        <h1 className="mb-1 text-2xl font-semibold">Create New Password</h1>
        <p className="mb-4 text-sm text-zinc-500">Use the reset link from the previous step.</p>
        <Input type="password" 
        value={password} 
        onChange={(e) => {
        const value = e.target.value;
        if (value.length <= 15){ 
        setPassword(e.target.value)}}} 
        placeholder="New password" minLength={8} required />
        <Button className="mt-4 w-full" type="submit" disabled={!uid || !token}>Reset Password</Button>
        {message ? <div className="mt-4 text-sm text-zinc-700">{message}</div> : null}
        <Link className="mt-4 block text-sm text-zinc-500 hover:text-zinc-900" href="/login">
          Back to login
        </Link>
      </form>
    </main>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<main className="min-h-screen bg-zinc-50 p-6" />}>
      <ResetPasswordForm />
    </Suspense>
  );
}
