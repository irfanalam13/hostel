"use client";

import { StaffShell } from "@/features/staff/components/primitives";
import { DepartmentManager } from "@/features/staff/components/DepartmentManager";

export default function StaffDepartmentsPage() {
  return (
    <StaffShell title="Departments" description="Organize departments and job designations.">
      <DepartmentManager />
    </StaffShell>
  );
}
