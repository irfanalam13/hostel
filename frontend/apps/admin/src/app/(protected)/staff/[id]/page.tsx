"use client";

import { useParams } from "next/navigation";

import { StaffShell } from "@/features/staff/components/primitives";
import { StaffProfileDetail } from "@/features/staff/components/StaffProfileDetail";

export default function StaffProfilePage() {
  const params = useParams();
  const id = Array.isArray(params?.id) ? params.id[0] : (params?.id as string);

  return (
    <StaffShell title="Staff profile" description="Complete employee record, roles and lifecycle.">
      {id ? <StaffProfileDetail staffId={id} /> : null}
    </StaffShell>
  );
}
