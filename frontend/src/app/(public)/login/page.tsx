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
  hostel_code?: string;
};

const HOSTEL_ID_RE = /^HTL-[A-Z0-9]{8}$/;

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

    if (!code) return toast.warning("Hostel ID is required.");
    if (!HOSTEL_ID_RE.test(code)) return toast.warning("Use the official Hostel ID format: HTL-XXXXXXXX.");
    if (!user) return toast.warning("Username is required.");
    if (!password) return toast.warning("Password is required.");

    setLoading(true);

    try {
      const data = await apiFetch<LoginResponse>("/auth/login/", {
        method: "POST",
        auth: false,
        body: JSON.stringify({ hostel_id: code, username: user, password }),
      });

      // Access/refresh JWTs are set as httpOnly cookies by the backend; the
      // auth layer records the session marker, hostel code and user context.
      authStore.setHostelCode(data?.hostel_code || code);
      onLoggedIn(
        data?.user ? ({ ...(data.user as any), role: data.user.role } as any) : null,
        data?.hostel_code || code
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
        <p className="text-gray-600 mb-6">Use your staff account + Hostel ID.</p>

        <div className="space-y-3">
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

          <Input
            id="username"
            name="username"
            label="Username"
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
        </div>

        <Button type="submit" className="mt-5 w-full" loading={loading}>
          {loading ? "Logging in..." : "Login"}
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

        <div className="mt-2 text-center text-sm">
          <Link href="/forgot-hostel-id" className="font-semibold text-blue-600 hover:underline">
            Forgot Hostel ID?
          </Link>
        </div>

        <div className="mt-4 text-xs text-gray-500 text-center">
          Official format: <span className="font-mono">HTL-XXXXXXXX</span>
        </div>
      </form>
    </main>
  );
}
