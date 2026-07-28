"use client";

import { useParams } from "next/navigation";
import { PlatformShell } from "@/features/platform/components/primitives";
import { HostelDetailView } from "@/features/platform/components/HostelDetailView";

export default function PlatformHostelDetailPage() {
  const params = useParams<{ id: string }>();

  return (
    <PlatformShell title="Hostel" description="Overview, students, staff and rooms — read-only.">
      <HostelDetailView id={params.id} />
    </PlatformShell>
  );
}
