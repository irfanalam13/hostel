"use client";

import React, { useState } from "react";
import type { Hostel, HostelCreateInput } from "../types/tenants.types";
import { Button } from "@hostel/ui";
import { Input } from "@hostel/ui";

export function HostelForm({
  initial,
  onSubmit,
  submitLabel = "Save",
}: {
  initial?: Partial<Hostel>;
  onSubmit: (payload: HostelCreateInput) => Promise<void>;
  submitLabel?: string;
}) {
  const [name, setName] = useState(initial?.name ?? "");
  const [code, setCode] = useState(initial?.code ?? "");
  const [phone, setPhone] = useState(initial?.phone ?? "");
  const [address, setAddress] = useState(initial?.address ?? "");
  const [isActive, setIsActive] = useState(initial?.is_active ?? true);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await onSubmit({
        name: name.trim(),
        code: code.trim() || undefined,
        phone: phone.trim() || undefined,
        address: address.trim() || undefined,
        is_active: isActive,
      });
      setName("");
      setCode("");
      setPhone("");
      setAddress("");
      setIsActive(true);
    } catch (err: any) {
      setError(err?.message || "Failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={submit} className="rounded-xl border border-zinc-200 bg-white p-4 space-y-3">
      <div className="font-semibold">Hostel</div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <Input placeholder="Name" value={name} onChange={(e: any) => setName(e.target.value)} />
        <Input placeholder="Code (auto if blank)" value={code} onChange={(e: any) => setCode(e.target.value)} />
        <Input placeholder="Phone" value={phone} onChange={(e: any) => setPhone(e.target.value)} />
        <Input placeholder="Address" value={address} onChange={(e: any) => setAddress(e.target.value)} />
      </div>

      <label className="flex items-center gap-2 text-sm text-zinc-700">
        <input
          type="checkbox"
          checked={isActive}
          onChange={(e) => setIsActive(e.target.checked)}
        />
        Active
      </label>

      {error && <div className="text-sm text-red-600">{error}</div>}

      <Button type="submit" disabled={loading || !name.trim()}>
        {loading ? "Saving..." : submitLabel}
      </Button>
    </form>
  );
}
