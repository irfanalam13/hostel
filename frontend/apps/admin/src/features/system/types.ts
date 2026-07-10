// Mirrors backend/apps/dashboard/system_views.py SystemStatusView response.

export interface SystemStatus {
  users: {
    members: number;
    online: number;
    offline: number;
    installed_active: number;
  };
  pwa: {
    push_subscribers: number;
    notifications_configured: boolean;
    app_version: string;
  };
  sync: {
    pending: number;
    failed: number;
  };
  background_tasks: {
    scheduled_notifications: number;
    sending_notifications: number;
    pending_deliveries: number;
    total: number;
  };
  api_health: {
    status: "ok" | "degraded";
    database: boolean;
    cache: boolean;
    celery: boolean;
  };
  server_time: string;
}

export interface HeartbeatPayload {
  installed: boolean;
  sw_version: string;
  app_version: string;
}

/** Client app version, inlined at build time (falls back to a default). */
export const APP_VERSION = process.env.NEXT_PUBLIC_APP_VERSION?.trim() || "1.0.0";
