"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Input } from "@/shared/ui/Input";
import { Button } from "@/shared/ui/Button";
import { apiFetch } from "@/shared/api/apiClient";
import { authStore } from "@/shared/auth/auth.store";
import { useToast } from "@/shared/ui/toast/ToastProvider";
import { useAuth } from "@/shared/auth/AuthProvider";

type LoginResponse = {
  detail?: string;
  user?: { role?: string };
};

function extractErrorMessage(data: any) {
  if (!data) return "Login failed";
  if (typeof data === "string") return data;
  if (data.detail) return String(data.detail);
  if (data.non_field_errors?.length) return String(data.non_field_errors[0]);

  if (typeof data === "object") {
    const values = Object.values(data);
    if (values.length) {
      const first = values[0] as any;
      if (Array.isArray(first) && first.length) return String(first[0]);
      if (typeof first === "string") return first;
    }
  }
  return "Login failed";
}

export default function LoginPage() {
  const router = useRouter();
  const toast = useToast();
  const { onLoggedIn } = useAuth();

  const [hostelCode, setHostelCode] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const [loading, setLoading] = useState(false);

  // Prefill hostel code if saved
  useEffect(() => {
    const saved = authStore.getHostelCode();
    if (saved) setHostelCode(saved);
  }, []);

  async function onLogin(e: React.FormEvent) {
    e.preventDefault();
    if (loading) return;

    const code = hostelCode.trim();
    const user = username.trim();

    if (!code) return toast.warning("Hostel code is required.");
    if (!user) return toast.warning("Username is required.");
    if (!password) return toast.warning("Password is required.");

    setLoading(true);

    try {
      const data = await apiFetch<LoginResponse>("/auth/login/", {
        method: "POST",
        auth: false,
        headers: { "X-Hostel-Code": code },
        body: JSON.stringify({ username: user, password }),
      });

      // Access/refresh JWTs are set as httpOnly cookies by the backend; the
      // auth layer records the session marker, hostel code and user context.
      authStore.setHostelCode(code);
      onLoggedIn(
        data?.user ? ({ ...(data.user as any), role: data.user.role } as any) : null,
        code
      );

      toast.success("Welcome back!", "Login successful");
      // replace() avoids a back-button bounce to the login screen.
      router.replace("/dashboard");
    } catch (e: any) {
      const msg =
        typeof e?.data !== "undefined"
          ? extractErrorMessage(e.data)
          : e?.message || "Something went wrong";
      toast.error(msg, "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen grid place-items-center p-6 bg-gray-50">
      <form
        onSubmit={onLogin}
        className="max-w-md w-full bg-white border rounded-2xl p-6 shadow-sm"
      >
        <h1 className="text-2xl font-bold mb-1">Login</h1>
        <p className="text-gray-600 mb-6">Use your staff account + hostel code.</p>

        <div className="space-y-3">
          <Input
            id="hostel_code"
            name="hostel_code"
            label="Hostel Code"
            value={hostelCode}
            onChange={(e) => {

            const value = e.target.value;
            if (value.length <= 15){
              
              setHostelCode(e.target.value)
              }
            }}
            placeholder="e.g. H-3F9A1C"
            required
            autoComplete="off"
          />

          <Input
            id="username"
            name="username"
            label="Username"
            value={username}
            onChange={(e) => {

            const value = e.target.value;
            if (value.length <= 15){
              setUsername(e.target.value)
              }
            }}
            required
            autoComplete="username"
          />

          <Input
            id="password"
            name="password"
            label="Password"
            type="password"
            value={password}
            onChange={(e) => {

            const value = e.target.value;
            if (value.length <= 15){
              setPassword(e.target.value)
              }
            }}
            required
            autoComplete="current-password"
          />
        </div>

        <Button type="submit" className="mt-5 w-full" loading={loading}>
          {loading ? "Logging in…" : "Login"}
        </Button>

        <div className="mt-4 text-center text-sm">
          <span className="text-gray-600">New hostel?</span>
          <Link href="/signup" className="ml-1 font-semibold text-blue-600 hover:underline">
            Create account
          </Link>
        </div>

        <div className="mt-2 text-center text-sm">
          <Link href="/forgot-password" className="font-semibold text-blue-600 hover:underline">
            Forgot password?
          </Link>
        </div>

        <div className="mt-4 text-xs text-gray-500 text-center">
          Tenant header used: <span className="font-mono">X-Hostel-Code</span>
        </div>
      </form>
    </main>
  );
}
