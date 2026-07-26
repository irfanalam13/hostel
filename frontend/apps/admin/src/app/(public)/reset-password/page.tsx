"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useState, useEffect } from "react";
import { authApi } from "@/features/auth/api/auth.api";
import { Button } from "@hostel/ui";
import { Input } from "@hostel/ui";

function ResetPasswordForm() {
  const params = useSearchParams();
  const [emailOrUsername, setEmailOrUsername] = useState("");
  const [otp, setOtp] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const val = params.get("email_or_username") || "";
    if (val) {
      setEmailOrUsername(val);
    }
  }, [params]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (loading) return;
    setLoading(true);
    try {
      const res = await authApi.resetPassword({
        email_or_username: emailOrUsername,
        otp: otp.trim(),
        new_password: password,
      });
      setMessage(res.detail);
    } catch (err: any) {
      setMessage(err?.message || "Failed to reset password.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-zinc-50 p-6">
      <form onSubmit={submit} className="mx-auto mt-16 max-w-md rounded-2xl border bg-white p-6 shadow-sm">
        <h1 className="mb-1 text-2xl font-semibold">Create New Password</h1>
        <p className="mb-4 text-sm text-zinc-500">Enter the 6-digit OTP code sent to your email.</p>
        
        <div className="space-y-3">
          <Input 
            value={emailOrUsername} 
            onChange={(e) => setEmailOrUsername(e.target.value)} 
            placeholder="Username or email" 
            required 
          />
          <Input 
            value={otp} 
            onChange={(e) => {
              const val = e.target.value;
              if (val.length <= 6) setOtp(val);
            }} 
            placeholder="6-digit OTP code" 
            maxLength={6}
            required 
          />
          <Input 
            type="password" 
            value={password} 
            onChange={(e) => {
              const value = e.target.value;
              if (value.length <= 15) setPassword(value);
            }} 
            placeholder="New password" 
            minLength={8} 
            required 
          />
        </div>

        <Button className="mt-4 w-full" type="submit" loading={loading}>
          Reset Password
        </Button>
        
        {message ? <div className="mt-4 text-sm text-zinc-700 bg-zinc-100 p-3 rounded-lg">{message}</div> : null}
        
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
