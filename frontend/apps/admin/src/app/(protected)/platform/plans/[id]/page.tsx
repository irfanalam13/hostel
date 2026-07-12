"use client";

import { useParams } from "next/navigation";
import { PlatformShell } from "@/features/platform/components/primitives";
import { PlanEditor } from "@/features/platform/components/PlanEditor";

export default function PlatformPlanEditorPage() {
  const params = useParams();
  const id = Array.isArray(params.id) ? params.id[0] : params.id;

  return (
    <PlatformShell title="Edit plan" description="Details, features and limits.">
      {id ? <PlanEditor planId={id} /> : null}
    </PlatformShell>
  );
}
