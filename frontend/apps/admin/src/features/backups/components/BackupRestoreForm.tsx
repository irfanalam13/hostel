// src/features/backups/components/BackupRestoreForm.tsx
"use client";

import React, { useMemo, useState } from "react";
import { restoreBackup } from "@/features/backups/api/backups.api";

type Props = {
  hostelId: string | null;
  onDone: () => void;
};

export function BackupRestoreForm({ hostelId, onDone }: Props) {
  const [rawJson, setRawJson] = useState("");
  const [confirmText, setConfirmText] = useState("");
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  const looksLikeJson = useMemo(() => {
    const t = rawJson.trim();
    return t.startsWith("{") && t.endsWith("}");
  }, [rawJson]);

  async function onRestore() {
    if (!hostelId) return setMsg("Hostel ID is required.");
    if (!rawJson.trim()) return setMsg("Paste backup JSON first.");
    if (!looksLikeJson) return setMsg("This doesn’t look like valid JSON.");
    if (confirmText.trim().toUpperCase() !== "RESTORE") {
      return setMsg('Type "RESTORE" to confirm.');
    }

    setLoading(true);
    setMsg(null);
    try {
      await restoreBackup(hostelId, rawJson);
      setMsg("Restored successfully.");
      setRawJson("");
      setConfirmText("");
      onDone();
    } catch (e: any) {
      setMsg(e?.message || "Restore failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="rounded-xl border p-4">
      <h2 className="text-base font-semibold text-red-600">Restore Backup (Danger)</h2>
      <p className="mt-1 text-sm text-gray-600">
        This will wipe hostel-scoped data (rooms, residents, stays, invoices, ledger, vacates) and restore from JSON.
      </p>

      <div className="mt-3 flex flex-col gap-2">
        <label className="text-sm font-medium">Paste Backup JSON</label>
        <textarea
          className="min-h-[220px] rounded-md border px-3 py-2 font-mono text-xs"
          placeholder='{"hostel": {...}, "rooms": [...], ...}'
          value={rawJson}
          onChange={(e) => setRawJson(e.target.value)}
        />

        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium">
            Confirm (type <span className="font-mono">RESTORE</span>)
          </label>
          <input
            className="rounded-md border px-3 py-2 text-sm"
            value={confirmText}
            onChange={(e) => setConfirmText(e.target.value)}
            placeholder="RESTORE"
          />
        </div>

        <button
          className="mt-2 w-fit rounded-md bg-red-600 px-4 py-2 text-sm text-white disabled:opacity-60"
          onClick={onRestore}
          disabled={loading}
        >
          Restore Now
        </button>

        {msg && <p className="text-sm text-gray-700">{msg}</p>}
      </div>
    </div>
  );
}
