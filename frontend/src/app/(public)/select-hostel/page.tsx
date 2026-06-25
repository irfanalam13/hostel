"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { hostelStore } from "@/shared/lib/hostel";
import { authStore } from "@/shared/auth/auth.store";

export default function SelectHostelPage() {
  const router = useRouter();
  const [code, setCode] = useState(hostelStore.getCode() || "");
  const [error, setError] = useState("");

  function save() {
    const c = code.trim();
    if (!c) {
      setError("Enter hostel code (example: abc123)");
      return;
    }
    hostelStore.set({ code: c });
    authStore.setHostelCode(c);
    router.push("/dashboard");
  }

  return (
    <div className="mx-auto max-w-md p-6">
      <h1 className="text-xl font-semibold text-zinc-900">Select Hostel</h1>
      <p className="mt-1 text-sm text-zinc-500">
        Enter your hostel code. This will be sent as{" "}
        <code>X-HOSTEL-CODE</code> header on every API request.
      </p>

      <div className="mt-4 rounded-2xl border border-zinc-200 bg-white p-4">
        <label className="text-sm text-zinc-700">Hostel code</label>
        <input
          value={code}
          onChange={(e) => {
            const value = e.target.value;
            if (value.length <= 15){
            setCode(e.target.value)}}}
          placeholder="e.g. greenhostel"
          className="mt-2 w-full rounded-xl border border-zinc-200 px-3 py-2 outline-none focus:ring-2"
        />

        {error ? (
          <div className="mt-3 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {error}
          </div>
        ) : null}

        <button
          onClick={save}
          className="mt-4 w-full rounded-xl bg-zinc-900 px-3 py-2 text-sm font-medium text-white hover:bg-zinc-800"
        >
          Continue
        </button>
      </div>
    </div>
  );
}
