"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { hostelStore } from "@hostel/utils";
import { authStore } from "@hostel/auth";

export default function SelectHostelPage() {
  const router = useRouter();
  const [code, setCode] = useState(hostelStore.getCode() || "");
  const [error, setError] = useState("");
  const hostelIdPattern = /^HTL-[A-Z0-9]{8}$/;

  function save() {
    const c = code.trim().toUpperCase();
    if (!c) {
      setError("Enter your Hostel ID.");
      return;
    }
    if (!hostelIdPattern.test(c)) {
      setError("Use the official Hostel ID format: HTL-XXXXXXXX.");
      return;
    }
    hostelStore.set({ code: c });
    authStore.setHostelCode(c);
    router.push("/login");
  }

  return (
    <div className="mx-auto max-w-md p-6">
      <h1 className="text-xl font-semibold text-zinc-900">Select Hostel</h1>
      <p className="mt-1 text-sm text-zinc-500">
        Enter your Hostel ID to prefill login. Access is verified by the secure login session.
      </p>

      <div className="mt-4 rounded-2xl border border-zinc-200 bg-white p-4">
        <label className="text-sm text-zinc-700">Hostel ID</label>
        <input
          value={code}
          onChange={(e) => {
            const value = e.target.value.toUpperCase().replace(/[^A-Z0-9-]/g, "");
            if (value.length <= 12) setCode(value);
          }}
          placeholder="e.g. HTL-7F4D91A2"
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
