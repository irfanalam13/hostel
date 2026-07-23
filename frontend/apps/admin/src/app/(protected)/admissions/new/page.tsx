"use client";

import { useRouter } from "next/navigation";
import { createAdmission } from "@/features/admissions/api";
import type { AdmissionRequest } from "@/features/admissions/types";
import { AdmissionForm } from "@/features/admissions/components/AdmissionForm";
import { Topbar } from "@/components/shell/Topbar";
import { useToast } from "@hostel/ui";

export default function NewAdmissionPage() {
  const router = useRouter();
  const toast = useToast();

  async function submit(payload: Partial<AdmissionRequest>) {
    try {
      const created = await createAdmission(payload);
      toast.success(`Application ${created.application_number} created.`);
      router.push("/admissions");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to create application.");
      throw err;
    }
  }

  return (
    <div>
      <Topbar title="New Admission" />
      <div className="mx-auto max-w-5xl px-4 py-4 sm:px-6">
        <AdmissionForm
          submitLabel="Create application"
          onSubmit={submit}
          onCancel={() => router.push("/admissions")}
        />
      </div>
    </div>
  );
}
