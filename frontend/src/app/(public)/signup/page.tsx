// "use client";

// import React, { useState } from "react";
// import { useRouter } from "next/navigation";
// import Link from "next/link";
// import { Input } from "@/shared/ui/Input";
// import { Button } from "@/shared/ui/Button";
// import { apiFetch } from "@/shared/api/apiClient";
// import { authStore } from "@/shared/auth/auth.store";

// function extractFirstError(data: any): string {
//   if (!data) return "Signup failed";
//   if (typeof data === "string") return data;

//   if (data.detail) return String(data.detail);
//   if (data.non_field_errors?.length) return String(data.non_field_errors[0]);

//   if (typeof data === "object") {
//     const values = Object.values(data);
//     if (values.length) {
//       const first = values[0] as any;
//       if (Array.isArray(first) && first.length) return String(first[0]);
//       if (typeof first === "string") return first;
//     }
//   }
//   return "Signup failed";
// }

// export default function SignupPage() {
//   const router = useRouter();

//   const [hostelName, setHostelName] = useState("");
//   const [hostelPhone, setHostelPhone] = useState("");
//   const [hostelAddress, setHostelAddress] = useState("");
//   const [ownerName, setOwnerName] = useState("");

//   const [username, setUsername] = useState("");
//   const [email, setEmail] = useState("");

//   const [password, setPassword] = useState("");
//   const [password2, setPassword2] = useState("");

//   const [loading, setLoading] = useState(false);
//   const [err, setErr] = useState("");
//   const [createdHostelCode, setCreatedHostelCode] = useState<string | null>(
//     null
//   );

//   async function onSignup(e: React.FormEvent) {
//     e.preventDefault();
//     if (loading) return;

//     setErr("");
//     setCreatedHostelCode(null);

//     const payload: any = {
//       hostel_name: hostelName.trim(),
//       hostel_phone: hostelPhone.trim() || "",
//       hostel_address: hostelAddress.trim() || "",
//       owner_name: ownerName.trim() || "",
//       username: username.trim(),
//       password,
//       password2,
//     };

//     const cleanEmail = email.trim();
//     if (cleanEmail) payload.email = cleanEmail;

//     // Frontend validation
//     if (!payload.hostel_name) return setErr("Hostel name is required.");
//     if (!payload.username) return setErr("Username is required.");
//     if (!password) return setErr("Password is required.");
//     if (password !== password2) return setErr("Passwords do not match.");

//     setLoading(true);
//     try {
//       // Signup is public => auth: false
//       const data = await apiFetch("/api/auth/signup/", {
//         method: "POST",
//         auth: false,
//         body: JSON.stringify(payload),
//       });

//       // Save hostel_code if backend returns it
//       const hostelCode: string | undefined = data?.hostel_code;
//       if (hostelCode) {
//         authStore.setHostelCode(hostelCode);
//         setCreatedHostelCode(hostelCode);
//       }

//       // If backend returns tokens => auto-login and go dashboard
//       if (data?.access && data?.refresh) {
//         authStore.setTokens(data.access, data.refresh);
//         router.push("/dashboard");
//         return;
//       }

//       // If no tokens => go login (hostel code will be prefilled)
//       router.push("/login");
//     } catch (e: any) {
//       // apiFetch throws Error(msg) already; keep fallback:
//       setErr(e?.message || extractFirstError(e) || "Something went wrong");
//     } finally {
//       setLoading(false);
//     }
//   }

//   return (
//     <main className="min-h-screen grid place-items-center p-6 bg-gray-50">
//       <form
//         onSubmit={onSignup}
//         className="max-w-md w-full bg-white border rounded-2xl p-6 shadow-sm"
//       >
//         <h1 className="text-2xl font-bold mb-1">Create Hostel</h1>
//         <p className="text-gray-600 mb-6">
//           Creates hostel + owner account and gives you a hostel code.
//         </p>

//         <div className="space-y-3">
//           <Input
//             id="hostel_name"
//             name="hostel_name"
//             label="Hostel Name"
//             value={hostelName}
//             onChange={(e) => setHostelName(e.target.value)}
//             required
//             autoComplete="organization"
//           />
//           <Input
//             id="hostel_phone"
//             name="hostel_phone"
//             label="Hostel Phone (optional)"
//             value={hostelPhone}
//             onChange={(e) => setHostelPhone(e.target.value)}
//             autoComplete="tel"
//           />
//           <Input
//             id="hostel_address"
//             name="hostel_address"
//             label="Hostel Address (optional)"
//             value={hostelAddress}
//             onChange={(e) => setHostelAddress(e.target.value)}
//             autoComplete="street-address"
//           />
//           <Input
//             id="owner_name"
//             name="owner_name"
//             label="Owner Name (optional)"
//             value={ownerName}
//             onChange={(e) => setOwnerName(e.target.value)}
//             autoComplete="name"
//           />

//           <hr className="my-2" />

//           <Input
//             id="username"
//             name="username"
//             label="Username"
//             value={username}
//             onChange={(e) => setUsername(e.target.value)}
//             required
//             autoComplete="username"
//           />
//           <Input
//             id="email"
//             name="email"
//             label="Email (optional)"
//             type="email"
//             value={email}
//             onChange={(e) => setEmail(e.target.value)}
//             autoComplete="email"
//           />
//           <Input
//             id="password"
//             name="password"
//             label="Password"
//             type="password"
//             value={password}
//             onChange={(e) => setPassword(e.target.value)}
//             required
//             autoComplete="new-password"
//           />
//           <Input
//             id="password2"
//             name="password2"
//             label="Confirm Password"
//             type="password"
//             value={password2}
//             onChange={(e) => setPassword2(e.target.value)}
//             required
//             autoComplete="new-password"
//           />
//         </div>

//         {err && <div className="mt-3 text-sm text-red-600">{err}</div>}

//         <Button type="submit" className="mt-5 w-full" disabled={loading}>
//           {loading ? "Creating..." : "Sign up"}
//         </Button>

//         {createdHostelCode && (
//           <div className="mt-4 text-sm bg-green-50 border border-green-200 rounded-xl p-3">
//             <div className="font-semibold text-green-800">Your Hostel Code:</div>
//             <div className="font-mono text-green-900 text-lg">
//               {createdHostelCode}
//             </div>
//             <div className="text-green-800 mt-2">
//               Use this code on the login page.
//             </div>
//           </div>
//         )}

//         <div className="mt-4 text-center text-sm">
//           <span className="text-gray-600">Already have an account?</span>
//           <Link
//             href="/login"
//             className="ml-1 font-semibold text-blue-600 hover:underline"
//           >
//             Login
//           </Link>
//         </div>
//       </form>
//     </main>
//   );
// }























"use client";

import React, { useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Input } from "@/shared/ui/Input";
import { Button } from "@/shared/ui/Button";
import { apiFetch } from "@/shared/api/apiClient";
import { authStore } from "@/shared/auth/auth.store";
import { hostelStore } from "@/shared/lib/hostel";

type SignupResponse = {
  user?: { role?: string };
  hostel_code?: string | null;
  access?: string;
  refresh?: string;
};

function extractFirstError(data: any): string {
  if (!data) return "Signup failed";
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
  return "Signup failed";
}

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

  const [hostelName, setHostelName] = useState("");
  const [hostelPhone, setHostelPhone] = useState("");
  const [hostelAddress, setHostelAddress] = useState("");
  const [ownerName, setOwnerName] = useState("");

  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");

  const [password, setPassword] = useState("");
  const [password2, setPassword2] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [showPw2, setShowPw2] = useState(false);

  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  const [createdHostelCode, setCreatedHostelCode] = useState<string | null>(null);
  const [signupDone, setSignupDone] = useState(false);

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

  const canSubmit = useMemo(() => {
    if (loading) return false;
    if (!hostelName.trim()) return false;
    if (!usernameOk) return false;
    if (!password) return false;
    if (password !== password2) return false;
    if (!phoneOk) return false;
    return true;
  }, [loading, hostelName, usernameOk, password, password2, phoneOk]);

  async function onSignup(e: React.FormEvent) {
    e.preventDefault();
    if (loading) return;

    setErr("");
    setCreatedHostelCode(null);
    setSignupDone(false);

    const payload: any = {
      hostel_name: hostelName.trim(),
      hostel_phone: hostelPhone.trim() || "",
      hostel_address: hostelAddress.trim() || "",
      owner_name: ownerName.trim() || "",
      username: username.trim(),
      password,
      password2,
    };

    const cleanEmail = email.trim();
    if (cleanEmail) payload.email = cleanEmail;

    // Frontend validation
    if (!payload.hostel_name) return setErr("Hostel name is required.");
    if (!payload.username) return setErr("Username is required.");
    if (!usernameOk) return setErr("Username must be 3+ chars and only a-z, 0-9, dot, underscore.");
    if (!phoneOk) return setErr("Phone looks invalid. Use digits only (optionally +).");
    if (!password) return setErr("Password is required.");
    if (password.length < 8) return setErr("Password should be at least 8 characters.");
    if (password !== password2) return setErr("Passwords do not match.");

    setLoading(true);
    try {
      const data = await apiFetch<SignupResponse>("/auth/signup/", {
        method: "POST",
        auth: false,
        body: JSON.stringify(payload),
      });

      const hostelCode = data?.hostel_code || undefined;
      if (hostelCode) {
        authStore.setHostelCode(hostelCode);
        hostelStore.set({ code: hostelCode });
        setCreatedHostelCode(hostelCode);
      }

      // Backend issues auth cookies on signup; mark the session active.
      authStore.setAuthed();
      if (data.user?.role) localStorage.setItem("role", data.user.role);

      // Editable UX: stay on page and show success box
      setSignupDone(true);
    } catch (e: any) {
      // apiFetch throws Error(message). If backend returned structure, show it:
      setErr(e?.message || "Signup failed");
    } finally {
      setLoading(false);
    }
  }

  async function copyCode() {
    if (!createdHostelCode) return;
    try {
      await navigator.clipboard.writeText(createdHostelCode);
    } catch {
      // fallback: ignore
    }
  }

  function resetForm() {
    setHostelName("");
    setHostelPhone("");
    setHostelAddress("");
    setOwnerName("");
    setUsername("");
    setEmail("");
    setPassword("");
    setPassword2("");
    setErr("");
    setCreatedHostelCode(null);
    setSignupDone(false);
  }

  return (
    <main className="min-h-screen grid place-items-center p-6 bg-gray-50">
      <form
        onSubmit={onSignup}
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
            if (value.length <= 15){
              
              setHostelName(e.target.value)
              }
            }}
            required
            autoComplete="organization"
          />

          <Input
            id="hostel_phone"
            name="hostel_phone"
            label="Hostel Phone (optional)"
            value={hostelPhone}
            onChange={(e) => {
              const value = e.target.value;
              if (value.length <=12) {
              setHostelPhone(value);
              }
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
              if (value.length <= 30) {
              setHostelAddress(value)
              }           
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
            if (value.length <= 15){
              
            setOwnerName(e.target.value)
            }
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
            if (value.length <= 30){
              setUsername(e.target.value)
              }
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
            label="Email (optional)"
            type="email"
            value={email}
            onChange={(e) => {

            const value = e.target.value;
            if (value.length <= 30){
              setEmail(e.target.value)
              }
            }}
            autoComplete="email"
          />

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
            if (value.length <= 15){
              setPassword(e.target.value)
              }
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
            if (value.length <= 15){
              setPassword2(e.target.value)
              }
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
          <Button type="submit" className="w-full" disabled={!canSubmit}>
            {loading ? "Creating..." : "Sign up"}
          </Button>
          <Button type="button" onClick={resetForm} disabled={loading}>
            Reset
          </Button>
        </div>

        {signupDone && (
          <div className="mt-4 text-sm bg-green-50 border border-green-200 rounded-xl p-3">
            <div className="font-semibold text-green-800">Signup successful</div>

            {createdHostelCode ? (
              <>
                <div className="mt-2 font-semibold text-green-800">Your Hostel ID:</div>
                <div className="font-mono text-green-900 text-lg">{createdHostelCode}</div>

                <div className="mt-3 flex gap-2">
                  <Button type="button" onClick={copyCode}>
                    Copy ID
                  </Button>
                  <Button type="button" onClick={() => router.push("/login")}>
                    Go to login
                  </Button>
                  <Button type="button" onClick={() => router.push("/dashboard")}>
                    Go to dashboard
                  </Button>
                </div>

                <div className="text-green-800 mt-2">
                  Use this Hostel ID on the login page.
                </div>
              </>
            ) : (
              <div className="mt-2 text-green-800">
                Hostel created, but Hostel ID was not returned by API.
              </div>
            )}
          </div>
        )}

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
