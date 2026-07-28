import type { ComponentType } from "react";
import {
  BarChart3,
  Boxes,
  Building2,
  Flag,
  GitCompare,
  History,
  IdCard,
  LayoutDashboard,
  Layers,
  LifeBuoy,
  ShieldAlert,
  ShieldPlus,
  Siren,
  Users,
} from "lucide-react";

export type PlatformSection = {
  id: string;
  label: string;
  description: string;
  href: string;
  icon: ComponentType<{ className?: string }>;
};

/** Single source of truth for the platform panel navigation. */
export const PLATFORM_SECTIONS: PlatformSection[] = [
  {
    id: "home",
    label: "Overview",
    description: "Subscription platform overview and quick actions",
    href: "/platform",
    icon: LayoutDashboard,
  },
  {
    id: "plans",
    label: "Plans",
    description: "Create, price and configure subscription plans",
    href: "/platform/plans",
    icon: Boxes,
  },
  {
    id: "comparison",
    label: "Comparison",
    description: "Feature/limit matrix across all plans",
    href: "/platform/comparison",
    icon: GitCompare,
  },
  {
    id: "catalog",
    label: "Catalog",
    description: "Features, categories and limit definitions",
    href: "/platform/catalog",
    icon: Layers,
  },
  {
    id: "subscriptions",
    label: "Subscriptions",
    description: "Assign plans to hostels and view lifecycle history",
    href: "/platform/subscriptions",
    icon: Building2,
  },
  {
    id: "hostels",
    label: "Hostels",
    description: "Every workspace's own students, revenue and dues",
    href: "/platform/hostels",
    icon: Users,
  },
  {
    id: "overrides",
    label: "Overrides",
    description: "Per-hostel feature grants and limit overrides",
    href: "/platform/overrides",
    icon: ShieldPlus,
  },
  {
    id: "analytics",
    label: "Analytics",
    description: "Revenue (MRR/ARR), plan distribution and feature adoption",
    href: "/platform/analytics",
    icon: BarChart3,
  },
  {
    id: "ops",
    label: "Operations",
    description: "Announcements, scheduled maintenance, incidents and feature flags",
    href: "/platform/ops",
    icon: Siren,
  },
  {
    id: "accounts",
    label: "Accounts",
    description: "Every user account across tenants and the plan they're on",
    href: "/platform/accounts",
    icon: IdCard,
  },
  {
    id: "audit",
    label: "Audit Log",
    description: "Searchable, tamper-evident trail of every platform action",
    href: "/platform/audit",
    icon: History,
  },
  {
    id: "security",
    label: "Security",
    description: "Threat events, IP rules, reputation and the emergency kill switch",
    href: "/platform/security",
    icon: ShieldAlert,
  },
  {
    id: "moderation",
    label: "Moderation",
    description: "Flagged reviews awaiting a decision",
    href: "/platform/moderation",
    icon: Flag,
  },
  {
    id: "disaster-recovery",
    label: "Disaster Recovery",
    description: "Backup snapshots, restore runs and DR mode",
    href: "/platform/disaster-recovery",
    icon: LifeBuoy,
  },
];
