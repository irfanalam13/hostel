export type Level = "info" | "warning" | "critical";
export type Audience = "all" | "staff" | "admins";

export interface Announcement {
  id: string;
  title: string;
  body: string;
  level: Level;
  audience: Audience;
  is_active: boolean;
  dismissible: boolean;
  starts_at: string | null;
  ends_at: string | null;
  live: boolean;
  created_at: string;
}

export type MaintenanceStatus = "scheduled" | "in_progress" | "completed" | "cancelled";

export interface MaintenanceWindow {
  id: string;
  title: string;
  description: string;
  status: MaintenanceStatus;
  scheduled_start: string;
  scheduled_end: string;
  enforce_read_only: boolean;
  components: string[];
  is_current: boolean;
  created_at: string;
}

export type IncidentSeverity = "sev1" | "sev2" | "sev3" | "sev4";
export type IncidentStatus = "investigating" | "identified" | "monitoring" | "resolved";

export interface IncidentUpdate {
  id: string;
  incident: string;
  status: IncidentStatus;
  message: string;
  created_at: string;
}

export interface Incident {
  id: string;
  title: string;
  summary: string;
  severity: IncidentSeverity;
  status: IncidentStatus;
  components: string[];
  is_public: boolean;
  started_at: string;
  resolved_at: string | null;
  is_open: boolean;
  updates: IncidentUpdate[];
  created_at: string;
}

export type OverrideScheduleState = "active" | "scheduled" | "expired" | "revoked";

export interface FeatureFlagOverride {
  id: string;
  flag: string;
  flag_key: string;
  hostel_id: string | null;
  hostel_label: string | null;
  user: number | null;
  user_label: string | null;
  enabled: boolean;
  reason: string;
  starts_at: string | null;
  expires_at: string | null;
  is_active: boolean;
  is_live: boolean;
  schedule_state: OverrideScheduleState;
  created_at: string;
}

export interface LookupResult {
  id: string | number;
  label: string;
  code?: string;
  email?: string;
  role?: string;
}

export interface FeatureFlag {
  id: string;
  key: string;
  name: string;
  description: string;
  is_active: boolean;
  kill: boolean;
  rollout_percentage: number;
  allowed_hostels: string[];
  blocked_hostels: string[];
  allowed_roles: string[];
  overrides: FeatureFlagOverride[];
  created_at: string;
}

export interface OpsStatus {
  announcements: Announcement[];
  maintenance: MaintenanceWindow[];
  incidents: Incident[];
  flags: Record<string, boolean>;
  server_time: string;
}
