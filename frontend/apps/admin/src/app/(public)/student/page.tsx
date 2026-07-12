"use client";

import { WorkspaceLoginForm } from "@/features/auth/components/WorkspaceLoginForm";

/** Student portal login — student/resident accounts only. */
export default function StudentLoginPage() {
  return (
    <WorkspaceLoginForm
      portal="student"
      title="Student Portal"
      subtitle="Sign in to view your dues, attendance and notices."
    />
  );
}
