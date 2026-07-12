// Mirrors backend/apps/analytics/services.py build_report().

export interface AnalyticsReport {
  window_days: number;
  total_events: number;
  install: { prompts: number; accepted: number; dismissed: number; installed: number; rate: number };
  update: { available: number; applied: number; rate: number };
  offline_usage: { sessions: number; total_seconds: number; users: number };
  feature_adoption: { name: string; uses: number; users: number }[];
  push: { received: number; opened: number; open_rate: number };
  cache: { hits: number; misses: number; efficiency: number };
  sync: { success: number; failure: number; success_rate: number };
  device_types: Record<string, number>;
  browsers: Record<string, number>;
  errors: { total: number; daily: Record<string, number> };
}
