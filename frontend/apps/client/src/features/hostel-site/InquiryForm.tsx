"use client";

import React, { useState } from "react";
import { workspaceFromLocation } from "@hostel/utils";

function apiBase(): string {
  return (process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api").replace(/\/+$/, "");
}

/**
 * Public inquiry form. Posts straight to the workspace's inquiry endpoint —
 * the workspace is taken from the live hostname; the hidden "website" field
 * is the spam honeypot (humans never see it, bots fill it).
 */
export function InquiryForm({ roomOptions }: { roomOptions: string[] }) {
  const [form, setForm] = useState({ name: "", email: "", phone: "", room_interest: "", message: "" });
  const [honeypot, setHoneypot] = useState("");
  const [state, setState] = useState<"idle" | "sending" | "done" | "error">("idle");
  const [error, setError] = useState("");

  function set(field: keyof typeof form) {
    return (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
      setForm((f) => ({ ...f, [field]: e.target.value }));
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (state === "sending") return;
    setError("");
    setState("sending");
    try {
      const workspace = workspaceFromLocation();
      const res = await fetch(`${apiBase()}/website/public/inquiries/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(workspace ? { "X-Workspace": workspace } : {}),
        },
        body: JSON.stringify({ ...form, website: honeypot }),
      });
      if (!res.ok) {
        const body = (await res.json().catch(() => null)) as
          | { message?: string; errors?: Record<string, unknown>; data?: Record<string, unknown> }
          | null;
        const fields = (body?.errors || body?.data || {}) as Record<string, unknown>;
        const first = Object.values(fields)[0];
        throw new Error(
          (Array.isArray(first) && String(first[0])) ||
            body?.message ||
            "Could not send your inquiry. Please try again.",
        );
      }
      setState("done");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not send your inquiry.");
      setState("error");
    }
  }

  if (state === "done") {
    return (
      <div className="rounded-2xl border border-green-200 bg-green-50 p-6 text-center">
        <div className="text-3xl">✅</div>
        <p className="mt-2 font-semibold text-green-800">Thank you!</p>
        <p className="text-sm text-green-700">
          We received your inquiry and will get back to you soon.
        </p>
      </div>
    );
  }

  const input =
    "w-full rounded-[var(--site-radius)] border border-gray-300 bg-white px-3 py-2 text-sm " +
    "focus:outline-none focus:ring-2 focus:ring-[var(--site-primary)]";

  return (
    <form onSubmit={onSubmit} className="space-y-3" aria-label="Inquiry form">
      <div className="grid gap-3 sm:grid-cols-2">
        <input required placeholder="Your name *" value={form.name} onChange={set("name")}
               className={input} maxLength={120} />
        <input placeholder="Phone" value={form.phone} onChange={set("phone")}
               className={input} maxLength={30} />
        <input type="email" placeholder="Email" value={form.email} onChange={set("email")}
               className={input} maxLength={120} />
        <select value={form.room_interest} onChange={set("room_interest")} className={input}>
          <option value="">Interested room (optional)</option>
          {roomOptions.map((r) => (
            <option key={r} value={r}>{r}</option>
          ))}
        </select>
      </div>
      <textarea required placeholder="Your message *" value={form.message} onChange={set("message")}
                rows={4} className={input} maxLength={4000} />
      {/* Honeypot — visually hidden, tab-skipped; bots fill it, humans can't. */}
      <input
        type="text" value={honeypot} onChange={(e) => setHoneypot(e.target.value)}
        name="website" tabIndex={-1} autoComplete="off" aria-hidden="true"
        className="absolute -left-[9999px] h-0 w-0 opacity-0"
      />
      {error && <p className="text-sm text-red-600">{error}</p>}
      <button
        type="submit"
        disabled={state === "sending"}
        className="rounded-[var(--site-radius)] bg-[var(--site-primary)] px-5 py-2.5 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-60"
      >
        {state === "sending" ? "Sending…" : "Send inquiry"}
      </button>
    </form>
  );
}
