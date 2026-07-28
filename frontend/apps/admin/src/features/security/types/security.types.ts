/** Types for the Super-Admin security console. Mirrors apps.security's
 * serializers (mounted at /api/platform/security/). */

export type SecurityPosture = {
  enabled: boolean;
  mode: string | null;
  fail_strategy: string | null;
  waf_mode: string | null;
  bots_mode: string | null;
  kill: { rate_limiter: boolean; auth: boolean };
  config_generation: number;
};

export type SecuritySummary = {
  window_hours: number;
  generated_at: string;
  total_events: number;
  blocked_events: number;
  threat_events: number;
  threat_level: string;
  by_type: Record<string, number>;
  by_action: Record<string, number>;
  top_ips: { ip: string; count: number }[];
  top_paths: { path: string; count: number }[];
  posture: SecurityPosture;
  timeseries: { bucket: string | null; count: number }[];
};

export type SecurityEvent = {
  id: string;
  created_at: string;
  event_type: string;
  action: string;
  ip: string;
  method: string;
  path: string;
  user_agent: string;
  request_id: string;
  country: string;
  asn: string;
  threat_score: number;
  tenant_id: string | null;
  user_id: string | null;
  detail: Record<string, unknown>;
};

export type TopOffender = { ip: string; blocked: number };

export type IPRule = {
  id: string;
  cidr: string;
  action: "allow" | "deny" | "trust";
  tenant: string | null;
  active: boolean;
  expires_at: string | null;
  note: string;
  created_at: string;
};

export type SecuritySetting = {
  id: string;
  key: string;
  value: unknown;
  active: boolean;
  note: string;
  updated_at: string;
};

export type KillSwitchTarget = "rate_limiter" | "auth" | "waf" | "bots" | "maintenance" | "emergency";
