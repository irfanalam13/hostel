import { apiFetch } from "@hostel/api";
import type { BackupValidateResult, DRMode, DRStatus, RestoreResult } from "../types/dr.types";

const json = (body: unknown): RequestInit => ({ body: JSON.stringify(body) });

export const drApi = {
  status: () => apiFetch<DRStatus>("/admin/dr/status/"),

  setMode: (mode: DRMode, reason?: string) =>
    apiFetch<{ mode: DRMode; reason: string }>("/admin/dr/mode/", {
      method: "POST",
      ...json({ mode, reason }),
    }),

  validateBackup: (backupId: string) =>
    apiFetch<BackupValidateResult>(`/admin/backups/${backupId}/validate/`, { method: "POST", ...json({}) }),

  restore: (backupId: string, opts: { dryRun: boolean; force?: boolean; confirm?: string }) =>
    apiFetch<RestoreResult>("/admin/restore/", {
      method: "POST",
      ...json({
        backup_id: backupId,
        dry_run: opts.dryRun,
        force: opts.force ?? false,
        confirm: opts.confirm ?? "",
      }),
    }),
};
