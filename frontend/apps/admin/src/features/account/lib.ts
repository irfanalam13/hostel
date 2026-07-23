import type { AuthUser } from "@/features/auth/api/auth.api";

/** Human display name: "First Last" → falls back to username. */
export function displayName(user?: AuthUser | null): string {
  if (!user) return "—";
  const full = [user.first_name, user.last_name].filter(Boolean).join(" ").trim();
  return full || user.username || "—";
}

/** Up-to-two-letter avatar initials derived from the best available name. */
export function initials(user?: AuthUser | null): string {
  if (!user) return "?";
  const first = (user.first_name || "").trim();
  const last = (user.last_name || "").trim();
  if (first || last) {
    return `${first.charAt(0)}${last.charAt(0)}`.toUpperCase() || first.charAt(0).toUpperCase();
  }
  const u = (user.username || "").trim();
  return u.slice(0, 2).toUpperCase() || "?";
}

const ROLE_LABELS: Record<string, string> = {
  ADMIN: "Administrator",
  OWNER: "Owner",
  MANAGER: "Manager",
  STAFF: "Staff",
  ACCOUNTANT: "Accountant",
  WARDEN: "Warden",
  RESIDENT: "Resident",
};

export function roleLabel(role?: string | null): string {
  if (!role) return "Member";
  return ROLE_LABELS[role] || role;
}

/**
 * Deterministic gradient for the avatar so each account reads distinctly but
 * stays on-brand. Seeded from the username so it never changes for a user.
 */
export function avatarGradient(seed: string): string {
  let hash = 0;
  for (let i = 0; i < seed.length; i += 1) {
    hash = (hash << 5) - hash + seed.charCodeAt(i);
    hash |= 0;
  }
  const hue = Math.abs(hash) % 360;
  return `linear-gradient(135deg, hsl(${hue} 70% 52%), hsl(${(hue + 40) % 360} 72% 44%))`;
}

/** Friendly absolute date, e.g. "7 Jul 2026". */
export function formatDate(value?: string | null): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}

/** Date + time, e.g. "7 Jul 2026, 14:03". */
export function formatDateTime(value?: string | null): string {
  if (!value) return "Never";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "Never";
  return d.toLocaleString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** Compact relative time, e.g. "just now", "3h ago", "2d ago". Falls back to
 *  an absolute date for anything older than a week. */
export function relativeTime(value?: string | null): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "—";
  const secs = Math.round((Date.now() - d.getTime()) / 1000);
  if (secs < 45) return "just now";
  const mins = Math.round(secs / 60);
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  if (days < 7) return `${days}d ago`;
  return formatDate(value);
}

/** Coarse "Browser · OS" label from a User-Agent, matching the server helper. */
export function parseUserAgent(ua?: string | null): string {
  const s = (ua || "").toLowerCase();
  if (!s) return "Unknown device";
  const os = s.includes("android")
    ? "Android"
    : /iphone|ipad|ios/.test(s)
      ? "iOS"
      : s.includes("windows")
        ? "Windows"
        : /mac os|macintosh/.test(s)
          ? "macOS"
          : s.includes("linux")
            ? "Linux"
            : "";
  const browser = s.includes("edg")
    ? "Edge"
    : /chrome|crios/.test(s)
      ? "Chrome"
      : /firefox|fxios/.test(s)
        ? "Firefox"
        : s.includes("safari")
          ? "Safari"
          : "";
  return [browser, os].filter(Boolean).join(" · ") || "Unknown device";
}

export type ActionTone = "accent" | "success" | "warning" | "error" | "info" | "muted";

/** Human label + colour tone for an AuditEvent action code. */
export function actionMeta(action: string): { label: string; tone: ActionTone } {
  const map: Record<string, { label: string; tone: ActionTone }> = {
    login: { label: "Signed in", tone: "success" },
    logout: { label: "Signed out", tone: "muted" },
    create: { label: "Created", tone: "accent" },
    update: { label: "Updated", tone: "info" },
    delete: { label: "Deleted", tone: "error" },
    payment: { label: "Payment", tone: "success" },
    vacate: { label: "Vacate", tone: "warning" },
    export: { label: "Export", tone: "info" },
    backup: { label: "Backup", tone: "info" },
    restore: { label: "Restore", tone: "warning" },
    access_denied: { label: "Access denied", tone: "error" },
    auth_failed: { label: "Sign-in failed", tone: "error" },
  };
  return map[action] || { label: action.replace(/_/g, " ") || "Event", tone: "muted" };
}

/** CSS variable for an action tone. */
export function toneColor(tone: ActionTone): string {
  return `var(--${tone === "accent" ? "accent" : tone === "muted" ? "muted" : tone})`;
}

export type CompletionItem = { key: string; label: string; done: boolean };

/**
 * Profile completion derived from the fields we actually persist today. This
 * grows automatically as more profile fields (phone, avatar, address…) are
 * added in later increments.
 */
export function profileCompletion(user?: AuthUser | null): {
  percent: number;
  items: CompletionItem[];
} {
  const items: CompletionItem[] = [
    { key: "first_name", label: "Add your first name", done: !!user?.first_name?.trim() },
    { key: "last_name", label: "Add your last name", done: !!user?.last_name?.trim() },
    { key: "email", label: "Add a recovery email", done: !!user?.email?.trim() },
  ];
  const done = items.filter((i) => i.done).length;
  const percent = items.length ? Math.round((done / items.length) * 100) : 100;
  return { percent, items };
}

/** Rough client-side password strength (0–4) for inline feedback. */
export function passwordScore(pw: string): number {
  let score = 0;
  if (pw.length >= 8) score += 1;
  if (pw.length >= 12) score += 1;
  if (/[a-z]/.test(pw) && /[A-Z]/.test(pw)) score += 1;
  if (/\d/.test(pw) && /[^A-Za-z0-9]/.test(pw)) score += 1;
  return Math.min(score, 4);
}
