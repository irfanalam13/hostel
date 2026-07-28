/** Types for the Super-Admin disaster-recovery console. Mirrors
 * apps.backups.admin_api (mounted at /api/admin/, super-admin/DR-admin only).
 * Distinct from features/backups, which is the per-tenant self-service
 * snapshot/restore feature — this is the cross-tenant platform-admin view. */

export type DRMode = "normal" | "maintenance" | "emergency";

export type RestoreRunSummary = {
  id: string;
  hostel_id: string;
  status: string;
  dry_run: boolean;
  created_at: string;
};

export type DRStatus = {
  mode: DRMode;
  storage: Record<string, unknown>;
  recent_restores: RestoreRunSummary[];
};

export type RestoreResult = {
  run_id: string;
  status: string;
  dry_run: boolean;
  hostel: string;
  backup_id: string;
  pre_restore_snapshot: string | null;
  stats: Record<string, unknown>;
};

export type BackupValidateResult = {
  backup_id: string;
  valid: boolean;
  report: Record<string, unknown>;
};
