import type { ComponentType } from "react";
import {
  Archive,
  BarChart3,
  Bell,
  Building2,
  Code2,
  CreditCard,
  DatabaseBackup,
  Globe,
  HardDrive,
  Info,
  KeyRound,
  Languages,
  LayoutDashboard,
  LifeBuoy,
  Lock,
  Mail,
  MessageSquare,
  Network,
  Palette,
  Plug,
  ScrollText,
  Server,
  ShieldCheck,
  Users,
  Wallet,
  Webhook,
} from "lucide-react";

/**
 * Maturity of a settings section:
 *  - "ready"   → fully wired to real data / functional
 *  - "partial" → real but limited (reuses an existing preview surface)
 *  - "soon"    → designed placeholder, not yet wired to a backend
 */
export type SectionStatus = "ready" | "partial" | "soon";

export type SettingsSection = {
  /** URL slug: /settings/<id> (id "home" maps to /settings). */
  id: string;
  label: string;
  /** One-line summary shown in nav tooltips, search results and placeholders. */
  description: string;
  icon: ComponentType<{ className?: string }>;
  /** Extra terms to match in the settings search beyond label/description. */
  keywords: string[];
  status: SectionStatus;
  /** Bullet points describing what a "soon" section will eventually do. */
  roadmap?: string[];
};

export type SettingsGroup = {
  id: string;
  label: string;
  sections: SettingsSection[];
};

/**
 * Single source of truth for the Settings module: navigation, breadcrumbs,
 * search index and section resolution all derive from this. Adding a new
 * section is one entry here plus (optionally) a content component in the shell.
 */
export const SETTINGS_GROUPS: SettingsGroup[] = [
  {
    id: "overview",
    label: "Overview",
    sections: [
      {
        id: "home",
        label: "Home",
        description: "Workspace overview, health and quick actions",
        icon: LayoutDashboard,
        keywords: ["dashboard", "overview", "summary", "start"],
        status: "ready",
      },
    ],
  },
  {
    id: "workspace",
    label: "Workspace",
    sections: [
      {
        id: "general",
        label: "General",
        description: "Hostel name, contact details and admission defaults",
        icon: Building2,
        keywords: ["hostel", "name", "contact", "fees", "defaults", "business"],
        status: "ready",
      },
      {
        id: "workspace-overview",
        label: "Workspace Overview",
        description: "Identity, URL, subscription, people counts and quick actions",
        icon: LayoutDashboard,
        keywords: ["workspace", "overview", "url", "subscription", "storage", "counts", "owner"],
        status: "ready",
      },
      {
        id: "profile",
        label: "Workspace Profile",
        description: "Legal name, business information and regional settings",
        icon: Building2,
        keywords: ["profile", "legal", "business", "pan", "vat", "regional", "timezone", "currency", "language"],
        status: "ready",
      },
      {
        id: "branding",
        label: "Branding",
        description: "Logos, favicon and backgrounds across login pages and portals",
        icon: Palette,
        keywords: ["branding", "logo", "favicon", "cover", "login background", "banner"],
        status: "ready",
      },
      {
        id: "workspace-url",
        label: "Workspace URL",
        description: "Your permanent workspace username and URL; owner-only rename with redirects",
        icon: Globe,
        keywords: ["url", "username", "subdomain", "rename", "redirect", "domain"],
        status: "ready",
      },
      {
        id: "custom-domains",
        label: "Custom Domains",
        description: "Connect your own domain, verify DNS, manage SSL and white-label branding",
        icon: Globe,
        keywords: ["domain", "custom domain", "dns", "ssl", "https", "white label", "cname", "txt"],
        status: "ready",
      },
      {
        id: "preferences",
        label: "Preferences",
        description: "Public website, portals, inquiry and feature toggles",
        icon: ShieldCheck,
        keywords: ["preferences", "toggles", "maintenance", "portal", "inquiry", "gallery", "events"],
        status: "ready",
      },
      {
        id: "website",
        label: "Website Builder",
        description: "Your hostel's public website — sections, theme, SEO and inquiries",
        icon: Globe,
        keywords: [
          "website", "cms", "landing", "public", "builder", "sections", "hero",
          "theme", "seo", "publish", "inquiries", "gallery",
        ],
        status: "ready",
      },
      {
        id: "organization",
        label: "Organization",
        description: "Branches, departments and legal information",
        icon: Network,
        keywords: ["branches", "departments", "hierarchy", "legal", "company"],
        status: "soon",
        roadmap: [
          "Multiple hostels under one organization",
          "Departments and staff hierarchy",
          "Legal & registration details",
        ],
      },
      {
        id: "appearance",
        label: "Appearance",
        description: "Theme, contrast and interface density",
        icon: Palette,
        keywords: ["theme", "dark", "light", "contrast", "density", "accent", "color"],
        status: "partial",
      },
      {
        id: "localization",
        label: "Localization",
        description: "Language, timezone, currency and formats",
        icon: Languages,
        keywords: ["language", "timezone", "currency", "date", "region", "locale"],
        status: "soon",
        roadmap: [
          "Multi-language interface",
          "Configurable timezone & currency",
          "Regional date/number formats",
        ],
      },
    ],
  },
  {
    id: "people",
    label: "People & Access",
    sections: [
      {
        id: "team",
        label: "Team Management",
        description: "Invite members, assign roles and manage workspace access",
        icon: Users,
        keywords: ["team", "invite", "members", "roles", "staff", "remove", "access"],
        status: "ready",
      },
      {
        id: "users",
        label: "Users & Staff",
        description: "Invite staff, manage accounts and statuses",
        icon: Users,
        keywords: ["staff", "admins", "wardens", "invite", "accounts", "members"],
        status: "soon",
        roadmap: [
          "Invite and manage staff accounts",
          "Suspend, deactivate and restore users",
          "Bulk actions and account status",
        ],
      },
      {
        id: "roles",
        label: "Roles & Permissions",
        description: "Custom roles and the permission matrix",
        icon: ShieldCheck,
        keywords: ["rbac", "permissions", "roles", "matrix", "access control"],
        status: "soon",
        roadmap: [
          "Permission matrix across modules",
          "Custom roles and templates",
          "Role change history & audit",
        ],
      },
    ],
  },
  {
    id: "security",
    label: "Security",
    sections: [
      {
        id: "security",
        label: "Security",
        description: "Sessions, devices and account protection",
        icon: Lock,
        keywords: ["security", "sessions", "devices", "policy", "lockout", "mfa", "protection"],
        status: "ready",
      },
      {
        id: "authentication",
        label: "Authentication",
        description: "Login methods, 2FA and password policy",
        icon: KeyRound,
        keywords: ["login", "2fa", "mfa", "password", "policy", "sso", "magic link"],
        status: "soon",
        roadmap: [
          "Password policy configuration",
          "Two-factor authentication",
          "Login methods & session expiry",
        ],
      },
      {
        id: "activity",
        label: "Activity Logs",
        description: "Workspace-wide activity trail with search",
        icon: ScrollText,
        keywords: ["activity", "workspace log", "trail", "who", "changes", "history"],
        status: "ready",
      },
      {
        id: "audit",
        label: "Audit Logs",
        description: "Recent account and security events",
        icon: ScrollText,
        keywords: ["audit", "logs", "history", "events", "activity", "trail"],
        status: "partial",
      },
    ],
  },
  {
    id: "communication",
    label: "Communication",
    sections: [
      {
        id: "notifications",
        label: "Notifications",
        description: "Email, SMS and push notification preferences",
        icon: Bell,
        keywords: ["notifications", "alerts", "push", "reminders", "digest", "modules"],
        status: "ready",
      },
      {
        id: "email",
        label: "Email",
        description: "SMTP, templates and delivery logs",
        icon: Mail,
        keywords: ["email", "smtp", "templates", "sender", "delivery", "bounce"],
        status: "soon",
        roadmap: ["SMTP configuration", "Email templates", "Delivery & bounce logs"],
      },
      {
        id: "sms",
        label: "SMS",
        description: "Provider, templates and delivery reports",
        icon: MessageSquare,
        keywords: ["sms", "text", "provider", "templates", "delivery"],
        status: "soon",
        roadmap: ["SMS provider setup", "Message templates", "Delivery reports & usage"],
      },
    ],
  },
  {
    id: "billing",
    label: "Billing",
    sections: [
      {
        id: "billing",
        label: "Plan & Billing",
        description: "Subscription, invoices and storage usage",
        icon: CreditCard,
        keywords: ["billing", "subscription", "plan", "invoices", "seats", "upgrade"],
        status: "partial",
      },
      {
        id: "payments",
        label: "Payment Methods",
        description: "Gateways and receipt configuration",
        icon: Wallet,
        keywords: ["payments", "stripe", "khalti", "esewa", "gateway", "receipts"],
        status: "soon",
        roadmap: [
          "Stripe / Khalti / eSewa integrations",
          "Manual & bank-transfer payments",
          "Invoice & receipt templates",
        ],
      },
    ],
  },
  {
    id: "data",
    label: "Data",
    sections: [
      {
        id: "backups",
        label: "Backups",
        description: "Create, restore and schedule backups",
        icon: DatabaseBackup,
        keywords: ["backup", "restore", "snapshot", "recovery", "schedule", "retention"],
        status: "ready",
      },
      {
        id: "storage",
        label: "Storage",
        description: "On-device storage usage and cleanup",
        icon: HardDrive,
        keywords: ["storage", "cache", "usage", "cleanup", "quota", "disk"],
        status: "ready",
      },
      {
        id: "data",
        label: "Data Management",
        description: "Offline sync, import, export and retention",
        icon: Archive,
        keywords: ["data", "offline", "sync", "import", "export", "gdpr", "retention"],
        status: "ready",
      },
      {
        id: "reports",
        label: "Reports",
        description: "Scheduled and exported reports",
        icon: BarChart3,
        keywords: ["reports", "scheduled", "export", "analytics", "dashboards"],
        status: "soon",
        roadmap: ["Scheduled email reports", "Export defaults & templates", "Dashboard reports"],
      },
    ],
  },
  {
    id: "developer",
    label: "Developer",
    sections: [
      {
        id: "api",
        label: "API & Tokens",
        description: "API tokens, rate limits and access logs",
        icon: Code2,
        keywords: ["api", "tokens", "keys", "developer", "rate limit", "oauth"],
        status: "soon",
        roadmap: ["API tokens & scopes", "Rate limits & access logs", "OAuth-ready architecture"],
      },
      {
        id: "integrations",
        label: "Integrations",
        description: "Connect Slack, Google, WhatsApp and more",
        icon: Plug,
        keywords: ["integrations", "slack", "google", "whatsapp", "zapier", "connect"],
        status: "soon",
        roadmap: ["Google Workspace & Microsoft 365", "Slack / Discord / WhatsApp", "Zapier & webhooks"],
      },
      {
        id: "webhooks",
        label: "Webhooks",
        description: "Outbound event webhooks",
        icon: Webhook,
        keywords: ["webhooks", "events", "callbacks", "http", "endpoints"],
        status: "soon",
        roadmap: ["Register webhook endpoints", "Event subscriptions", "Delivery logs & retries"],
      },
    ],
  },
  {
    id: "system",
    label: "System",
    sections: [
      {
        id: "system",
        label: "System",
        description: "Environment, version and health checks",
        icon: Server,
        keywords: ["system", "environment", "version", "cache", "health", "maintenance"],
        status: "partial",
      },
      {
        id: "about",
        label: "About",
        description: "Versions, license and system status",
        icon: Info,
        keywords: ["about", "version", "license", "status", "credits"],
        status: "partial",
      },
      {
        id: "danger",
        label: "Danger Zone",
        description: "Protected owner actions: resets, archive, deletion request, export",
        icon: Lock,
        keywords: ["danger", "archive", "delete", "reset", "export", "import", "disable"],
        status: "ready",
      },
      {
        id: "help",
        label: "Help & Support",
        description: "Documentation, release notes and support",
        icon: LifeBuoy,
        keywords: ["help", "support", "docs", "documentation", "contact", "bug"],
        status: "soon",
        roadmap: ["Documentation & knowledge base", "Release notes", "Contact support & bug reports"],
      },
    ],
  },
];

/** Flat list of every section, in nav order. */
export const ALL_SECTIONS: SettingsSection[] = SETTINGS_GROUPS.flatMap((g) => g.sections);

/** Resolve a slug (or undefined → "home") to its section, or null if unknown. */
export function findSection(id?: string | null): SettingsSection | null {
  const slug = id && id.length ? id : "home";
  return ALL_SECTIONS.find((s) => s.id === slug) ?? null;
}

/** The group a section belongs to (for breadcrumbs). */
export function groupForSection(id: string): SettingsGroup | null {
  return SETTINGS_GROUPS.find((g) => g.sections.some((s) => s.id === id)) ?? null;
}

/** Canonical href for a section ("home" lives at /settings). */
export function sectionHref(id: string): string {
  return id === "home" ? "/settings" : `/settings/${id}`;
}

/** Rank sections against a free-text query for the in-shell search. */
export function searchSections(query: string): SettingsSection[] {
  const q = query.trim().toLowerCase();
  if (!q) return ALL_SECTIONS.filter((s) => s.id !== "home");
  const terms = q.split(/\s+/);
  return ALL_SECTIONS.filter((s) => {
    const haystack = [s.label, s.description, ...s.keywords].join(" ").toLowerCase();
    return terms.every((t) => haystack.includes(t));
  });
}

export const STATUS_META: Record<SectionStatus, { label: string; tone: string }> = {
  ready: { label: "Ready", tone: "var(--success)" },
  partial: { label: "Preview", tone: "var(--info)" },
  soon: { label: "Soon", tone: "var(--muted)" },
};
