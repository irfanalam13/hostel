export type AuditResult = "success" | "failure" | "denied";

export interface AuditEvent {
  id: number;
  sequence: number | null;
  created_at: string;
  action: string;
  result: AuditResult;
  status_code: number | null;
  duration_ms: number | null;
  actor: number | null;
  actor_label: string | null;
  hostel_id: string | null;
  branch_id: string | null;
  entity_type: string;
  entity_id: string;
  message: string;
  reason: string;
  changes: { old?: unknown; new?: unknown } | null;
  meta: Record<string, unknown>;
  ip_address: string | null;
  user_agent: string;
  request_id: string;
  prev_hash: string;
  content_hash: string;
}

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface AuditVerifyResult {
  ok: boolean;
  checked: number;
  first_bad_sequence: number | null;
  reason: string;
  errors: string[];
}

export interface AuditFilters {
  action?: string;
  result?: string;
  search?: string;
  created_after?: string;
  created_before?: string;
  page?: number;
}

export const AUDIT_ACTIONS = [
  "create", "update", "delete", "login", "logout", "payment", "vacate",
  "export", "backup", "restore", "maintenance", "access_denied", "auth_failed",
  "incident", "announcement", "feature_flag",
] as const;
