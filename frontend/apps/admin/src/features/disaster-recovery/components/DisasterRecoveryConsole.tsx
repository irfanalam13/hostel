"use client";

import React, { useEffect, useState } from "react";
import { Button, Input, Select, useConfirm, useToast } from "@hostel/ui";
import { Badge, Toggle } from "@/features/platform/components/primitives";
import { drApi } from "../api/dr.api";
import type { DRMode, DRStatus } from "../types/dr.types";

const MODE_TONE: Record<DRMode, string | undefined> = {
  normal: "var(--success)",
  maintenance: "var(--warning)",
  emergency: "var(--error)",
};

export function DisasterRecoveryConsole() {
  const toast = useToast();
  const confirm = useConfirm();
  const [status, setStatus] = useState<DRStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [nextMode, setNextMode] = useState<DRMode>("normal");
  const [reason, setReason] = useState("");

  const [backupId, setBackupId] = useState("");
  const [confirmCode, setConfirmCode] = useState("");
  const [dryRun, setDryRun] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const s = await drApi.status();
      setStatus(s);
      setNextMode(s.mode);
    } catch (e) {
      toast.error((e as Error).message, "Failed to load DR status");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const applyMode = async () => {
    if (!status || nextMode === status.mode) return;
    const yes = await confirm({
      title: `Switch DR mode to "${nextMode}"`,
      message:
        nextMode === "normal"
          ? "Restore normal platform operation."
          : `This puts the ENTIRE platform into ${nextMode} mode — every tenant is affected immediately. Are you sure?`,
      danger: nextMode !== "normal",
      confirmText: "Switch mode",
    });
    if (!yes) return;
    setBusy(true);
    try {
      await drApi.setMode(nextMode, reason);
      toast.success(`DR mode switched to ${nextMode}.`);
      setReason("");
      await load();
    } catch (e) {
      toast.error((e as Error).message, "Mode switch failed");
    } finally {
      setBusy(false);
    }
  };

  const validate = async () => {
    if (!backupId.trim()) return;
    setBusy(true);
    try {
      const r = await drApi.validateBackup(backupId.trim());
      toast[r.valid ? "success" : "error"](r.valid ? "Backup is valid." : "Backup failed validation.");
    } catch (e) {
      toast.error((e as Error).message, "Validation failed");
    } finally {
      setBusy(false);
    }
  };

  const restore = async () => {
    if (!backupId.trim()) return;
    if (!dryRun) {
      const yes = await confirm({
        title: "Destructive restore",
        message: "This overwrites the target hostel's live data from the backup. This cannot be undone.",
        danger: true,
        confirmText: "Restore now",
      });
      if (!yes) return;
    }
    setBusy(true);
    try {
      const r = await drApi.restore(backupId.trim(), { dryRun, force: !dryRun, confirm: confirmCode.trim() });
      toast.success(dryRun ? "Dry-run restore completed — no data was changed." : `Restore ${r.status}.`);
    } catch (e) {
      toast.error((e as Error).message, "Restore failed");
    } finally {
      setBusy(false);
    }
  };

  if (loading) return <div className="text-sm text-[var(--muted)]">Loading…</div>;
  if (!status) return null;

  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="rounded-xl border border-[var(--border)] p-4">
          <div className="text-xs text-[var(--muted)]">Current DR mode</div>
          <div className="mt-1">
            <Badge color={MODE_TONE[status.mode]}>{status.mode}</Badge>
          </div>
          <div className="mt-4 space-y-2">
            <Select
              label="Switch to"
              value={nextMode}
              onChange={(e) => setNextMode(e.target.value as DRMode)}
              options={[
                { value: "normal", label: "Normal" },
                { value: "maintenance", label: "Maintenance" },
                { value: "emergency", label: "Emergency" },
              ]}
            />
            <Input label="Reason" value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Why this change?" />
            <Button size="sm" disabled={busy || nextMode === status.mode} onClick={applyMode}>
              Apply
            </Button>
          </div>
        </div>

        <div className="rounded-xl border border-[var(--border)] p-4">
          <div className="text-xs text-[var(--muted)]">Storage usage</div>
          <pre className="mt-2 max-h-40 overflow-auto rounded-lg bg-[var(--background-secondary)] p-2 text-xs">
            {JSON.stringify(status.storage, null, 2)}
          </pre>
        </div>
      </div>

      <div className="rounded-xl border border-[var(--border)] p-4">
        <div className="mb-2 text-sm font-medium text-[var(--foreground)]">Recent restore runs</div>
        {status.recent_restores.length === 0 ? (
          <div className="text-xs text-[var(--muted)]">No restores have been run yet.</div>
        ) : (
          <ul className="space-y-1 text-sm">
            {status.recent_restores.map((r) => (
              <li key={r.id} className="flex items-center justify-between gap-2 border-b border-[var(--border)] py-1.5 last:border-0">
                <span className="font-mono text-xs text-[var(--foreground-secondary)]">{r.hostel_id}</span>
                <span className="text-[var(--foreground-secondary)]">{r.status}</span>
                {r.dry_run ? <Badge>dry-run</Badge> : null}
                <span className="text-[var(--muted)]">{new Date(r.created_at).toLocaleString()}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="rounded-xl border border-[var(--border)] p-4">
        <div className="mb-1 text-sm font-medium text-[var(--foreground)]">Validate / restore a specific backup</div>
        <p className="mb-3 text-xs text-[var(--muted)]">
          Requires the backup snapshot ID (find it via the tenant&apos;s own Backups page). A real restore also
          requires typing the target hostel&apos;s code to confirm — this matches the backend&apos;s own safety gate.
        </p>
        <div className="flex flex-wrap items-end gap-2">
          <Input label="Backup ID" value={backupId} onChange={(e) => setBackupId(e.target.value)} className="min-w-[16rem]" />
          <Button variant="secondary" size="sm" disabled={busy || !backupId.trim()} onClick={validate}>
            Validate
          </Button>
        </div>
        <div className="mt-3 flex flex-wrap items-end gap-2">
          <Input
            label="Confirm hostel code (required for a real restore)"
            value={confirmCode}
            onChange={(e) => setConfirmCode(e.target.value)}
            className="min-w-[14rem]"
          />
          <label className="flex items-center gap-2 pb-2 text-sm text-[var(--foreground-secondary)]">
            <Toggle checked={dryRun} onChange={setDryRun} /> Dry run
          </label>
          <Button
            variant={dryRun ? "secondary" : "primary"}
            size="sm"
            disabled={busy || !backupId.trim() || (!dryRun && !confirmCode.trim())}
            onClick={restore}
          >
            {dryRun ? "Run dry-run restore" : "Restore now"}
          </Button>
        </div>
      </div>
    </div>
  );
}
