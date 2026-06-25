// src/features/backups/api.ts
import { apiDownload, apiFetch } from "@/shared/api/apiClient";
import type { BackupSnapshot } from "../types/backups.types";

const BASE = "/backups/backups/";

export async function listBackups(): Promise<BackupSnapshot[]> {
  return apiFetch<BackupSnapshot[]>(BASE);
}

export async function createSnapshot(hostelId: string, note?: string) {
  return apiFetch<{ id: string; status: string }>(`${BASE}create_snapshot/`, {
    method: "POST",
    body: JSON.stringify({ hostel: hostelId, note: note || "" }),
  });
}

export async function scheduleNow(hostelId: string) {
  return apiFetch<{ status: string }>(`${BASE}schedule_now/`, {
    method: "POST",
    body: JSON.stringify({ hostel: hostelId }),
  });
}

export async function restoreBackup(hostelId: string, rawJson: string) {
  return apiFetch<{ status: string }>(`${BASE}restore/`, {
    method: "POST",
    body: JSON.stringify({ hostel: hostelId, json: rawJson }),
  });
}

export async function downloadBackup(snapshotId: string) {
  // filename is best-effort; backend sets Content-Disposition, but we also set one here
  const filename = `backup_${snapshotId}.json`;
  return apiDownload(`${BASE}${snapshotId}/download/`, filename);
}
