// src/features/backups/components/BackupCreateForm.tsx
"use client";

import React, { useState } from "react";
import { createSnapshot, scheduleNow } from "@/features/backups/api/backups.api";

type Props = {
  hostelId: string | null;
  onDone: () => void;
};

export function BackupCreateForm({ hostelId, onDone }: Props) {
  const [note, setNote] = useState("");
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  async function onCreate() {
    if (!hostelId) return setMsg("Hostel ID is required.");
    setLoading(true);
    setMsg(null);
    try {
      await createSnapshot(hostelId, note);
      setNote("");
      setMsg("Snapshot created.");
      onDone();
    } catch (e: any) {
      setMsg(e?.message || "Failed to create snapshot.");
    } finally {
      setLoading(false);
    }
  }

  async function onScheduleNow() {
    if (!hostelId) return setMsg("Hostel ID is required.");
    setLoading(true);
    setMsg(null);
    try {
      await scheduleNow(hostelId);
      setMsg("Backup scheduled (Celery task triggered).");
      onDone();
    } catch (e: any) {
      setMsg(e?.message || "Failed to schedule backup.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="rounded-xl border p-4">
      <h2 className="text-base font-semibold">Create Backup</h2>

      <div className="mt-3 flex flex-col gap-2">
        <label className="text-sm font-medium">Note (optional)</label>
        <input
          className="rounded-md border px-3 py-2 text-sm"
          placeholder="e.g. Before month-end changes"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          maxLength={255}
        />

        <div className="mt-2 flex gap-2">
          <button
            className="rounded-md bg-black px-4 py-2 text-sm text-white disabled:opacity-60"
            onClick={onCreate}
            disabled={loading}
          >
            Create Snapshot
          </button>

          <button
            className="rounded-md border px-4 py-2 text-sm disabled:opacity-60"
            onClick={onScheduleNow}
            disabled={loading}
          >
            Schedule Now
          </button>
        </div>

        {msg && <p className="text-sm text-gray-700">{msg}</p>}
      </div>
    </div>
  );
}
