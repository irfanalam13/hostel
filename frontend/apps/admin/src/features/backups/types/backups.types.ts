// src/features/backups/types.ts
export type HostelRef =
  | string
  | {
      id: string;
      name?: string;
      code?: string;
    };

export type BackupSnapshot = {
  id: string;
  hostel: HostelRef;
  kind: "manual" | "scheduled" | string;
  note?: string;
  file?: string;
  created_at?: string; // depends on your model
  created?: string;    // fallback if your model uses created
};
