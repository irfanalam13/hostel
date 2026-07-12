/**
 * Workspace (tenant) client-side domain logic.
 *
 * Mirrors the backend rules in `backend/apps/tenants/validators.py` and
 * `middleware.py` so the UI can give instant feedback and resolve the current
 * workspace from the hostname exactly the way the API does. The backend is
 * always authoritative — these checks exist for UX, not security.
 *
 * Everything except `workspaceStore` is pure (no browser APIs), so this
 * module is also safe to import from the Edge-runtime security proxy via
 * `@hostel/utils/workspace`.
 */

/** DNS-label shape: lowercase alnum, hyphens in the middle only. */
export const WORKSPACE_USERNAME_RE = /^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$/;

/** Mirror of the backend's BASE_RESERVED_WORKSPACE_NAMES. */
export const RESERVED_WORKSPACE_NAMES = new Set([
  "admin", "api", "www", "mail", "root", "dashboard", "system", "support",
  "login", "auth", "docs", "static", "media", "assets", "cdn", "status",
  "health", "monitor", "test", "app", "staging", "dev", "demo", "internal",
  "billing", "smtp", "imap", "pop", "ftp", "ns1", "ns2", "webmail",
  "signup", "register", "account", "accounts", "security", "help", "blog",
]);

const DNS_LABEL_MAX = 63;

export function workspaceUsernameLimits(): { min: number; max: number } {
  const min = Number(process.env.NEXT_PUBLIC_WORKSPACE_USERNAME_MIN_LENGTH || 3);
  const max = Math.min(
    Number(process.env.NEXT_PUBLIC_WORKSPACE_USERNAME_MAX_LENGTH || 32),
    DNS_LABEL_MAX,
  );
  return { min: Math.max(min, 1), max };
}

/** The wildcard base domain workspaces live under (e.g. "myhostel.com"). */
export function tenantBaseDomain(): string {
  return (process.env.NEXT_PUBLIC_TENANT_BASE_DOMAIN || "localhost").trim().toLowerCase();
}

/** Trim + lowercase — same normalization the backend applies. */
export function normalizeWorkspaceUsername(value: string): string {
  return (value || "").trim().toLowerCase();
}

export type WorkspaceUsernameCheck =
  | { ok: true; value: string }
  | {
      ok: false;
      value: string;
      reason: "required" | "too_short" | "too_long" | "invalid" | "reserved";
      message: string;
    };

/** Validate an (auto-normalized) workspace username. Mirrors the API's reasons. */
export function validateWorkspaceUsername(raw: string): WorkspaceUsernameCheck {
  const value = normalizeWorkspaceUsername(raw);
  const { min, max } = workspaceUsernameLimits();

  if (!value) {
    return { ok: false, value, reason: "required", message: "Workspace username is required." };
  }
  if (value.length < min) {
    return {
      ok: false, value, reason: "too_short",
      message: `Must be at least ${min} characters.`,
    };
  }
  if (value.length > max) {
    return {
      ok: false, value, reason: "too_long",
      message: `Must be at most ${max} characters.`,
    };
  }
  if (!WORKSPACE_USERNAME_RE.test(value)) {
    return {
      ok: false, value, reason: "invalid",
      message:
        "Use lowercase letters, numbers and hyphens only; it must start and end with a letter or number.",
    };
  }
  if (RESERVED_WORKSPACE_NAMES.has(value)) {
    return { ok: false, value, reason: "reserved", message: "This name is reserved." };
  }
  return { ok: true, value };
}

/** Derive a workspace-username candidate from free text (e.g. the hostel name). */
export function suggestWorkspaceUsername(name: string): string {
  const { max } = workspaceUsernameLimits();
  return normalizeWorkspaceUsername(name)
    .replace(/[^a-z0-9\s-]/g, "")
    .replace(/[\s_]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, max)
    .replace(/-+$/g, "");
}

const LOCAL_HOSTS = new Set(["localhost", "127.0.0.1", "0.0.0.0", "testserver"]);

function isIp(host: string): boolean {
  return /^\d{1,3}(\.\d{1,3}){3}$/.test(host) || host.includes(":");
}

/**
 * Extract the workspace label from a hostname, or null when the host is not
 * a workspace host (root domain, reserved label, localhost, IP, nested or
 * unrelated domain). Mirrors backend `extract_workspace_subdomain`.
 */
export function extractWorkspaceFromHost(hostWithPort: string): string | null {
  const host = (hostWithPort || "").split(":")[0].trim().toLowerCase().replace(/\.$/, "");
  if (!host || LOCAL_HOSTS.has(host) || isIp(host)) return null;

  const base = tenantBaseDomain();
  if (!base || host === base) return null;
  if (!host.endsWith("." + base)) return null;

  const label = host.slice(0, -(base.length + 1));
  if (label.includes(".")) return null; // nested subdomains are not tenant hosts
  if (RESERVED_WORKSPACE_NAMES.has(label)) return null;
  if (!WORKSPACE_USERNAME_RE.test(label)) return null;
  return label;
}

/** The workspace slug for the page currently loaded in the browser, if any. */
export function workspaceFromLocation(): string | null {
  if (typeof window === "undefined") return null;
  return extractWorkspaceFromHost(window.location.host);
}

/**
 * True when a hostname belongs to the platform itself (base domain family,
 * localhost, IP) — i.e. NOT a tenant's custom domain.
 */
export function isPlatformHost(hostWithPort: string): boolean {
  const host = (hostWithPort || "").split(":")[0].trim().toLowerCase().replace(/\.$/, "");
  if (!host || LOCAL_HOSTS.has(host) || isIp(host)) return true;
  if (host.endsWith(".localhost")) return true;
  const base = tenantBaseDomain();
  return host === base || host.endsWith("." + base);
}

/**
 * The custom tenant domain the page is currently served from, if any
 * (Prompt 05). Forwarded to the API as `X-Tenant-Host` in split-domain
 * deployments so the backend resolves the tenant from it — derived strictly
 * from the live location, never stored state.
 */
export function customDomainFromLocation(): string | null {
  if (typeof window === "undefined") return null;
  const host = window.location.host;
  return isPlatformHost(host) ? null : host.split(":")[0].toLowerCase();
}

/** Display/deep-link URL for a workspace, e.g. https://everest.myhostel.com */
export function workspaceUrlFor(slug: string): string {
  const base = tenantBaseDomain();
  const scheme =
    process.env.NEXT_PUBLIC_TENANT_URL_SCHEME || (base === "localhost" ? "http" : "https");
  return `${scheme}://${slug}.${base}`;
}

// ---------------------------------------------------------------------------
// Persisted workspace context (browser only)
// ---------------------------------------------------------------------------
type WorkspaceContext = {
  slug?: string;
  url?: string;
};

const KEY = "workspace_context_v1";

/**
 * Remembers the user's workspace across visits (e.g. after signup) so the app
 * can offer "continue to your workspace". Routing itself always trusts the
 * live hostname (`workspaceFromLocation`) — never this store — so stale
 * state can never point requests at the wrong tenant.
 */
export const workspaceStore = {
  get(): WorkspaceContext {
    if (typeof window === "undefined") return {};
    try {
      return JSON.parse(localStorage.getItem(KEY) || "{}") as WorkspaceContext;
    } catch {
      return {};
    }
  },

  set(ctx: WorkspaceContext) {
    if (typeof window === "undefined") return;
    try {
      localStorage.setItem(KEY, JSON.stringify(ctx));
    } catch {
      // storage unavailable — non-fatal, the store is a convenience only
    }
  },

  clear() {
    if (typeof window === "undefined") return;
    try {
      localStorage.removeItem(KEY);
    } catch {}
  },

  getSlug(): string | undefined {
    return this.get().slug?.trim() || undefined;
  },
};
