"use client";

import { StaffShell } from "@/features/staff/components/primitives";
import { StaffDirectory } from "@/features/staff/components/StaffDirectory";

export default function StaffDirectoryPage() {
  return (
    <StaffShell title="Directory" description="Browse, invite and manage your staff members.">
      <StaffDirectory />
    </StaffShell>
  );
}
