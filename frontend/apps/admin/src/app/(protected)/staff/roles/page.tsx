"use client";

import { StaffShell } from "@/features/staff/components/primitives";
import { RoleManager } from "@/features/staff/components/RoleManager";

export default function StaffRolesPage() {
  return (
    <StaffShell title="Roles & Permissions" description="Build custom roles and assign granular permissions.">
      <RoleManager />
    </StaffShell>
  );
}
