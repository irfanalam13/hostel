import type { ComponentType } from "react";
import { Building2, LayoutList, ShieldCheck } from "lucide-react";

export type StaffSection = {
  id: string;
  label: string;
  description: string;
  href: string;
  icon: ComponentType<{ className?: string }>;
};

/** Single source of truth for the Staff module sub-navigation. */
export const STAFF_SECTIONS: StaffSection[] = [
  {
    id: "directory",
    label: "Directory",
    description: "Browse, invite and manage staff members",
    href: "/staff",
    icon: LayoutList,
  },
  {
    id: "roles",
    label: "Roles & Permissions",
    description: "Build custom roles and assign granular permissions",
    href: "/staff/roles",
    icon: ShieldCheck,
  },
  {
    id: "departments",
    label: "Departments",
    description: "Organize departments and designations",
    href: "/staff/departments",
    icon: Building2,
  },
];
