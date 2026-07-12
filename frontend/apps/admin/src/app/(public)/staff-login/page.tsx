"use client";

import { WorkspaceLoginForm } from "@/features/auth/components/WorkspaceLoginForm";

/** Staff portal login (alias of /login, kept for the canonical portal URL). */
export default function StaffLoginPage() {
  return (
    <WorkspaceLoginForm
      portal="staff"
      title="Staff Login"
      subtitle="Sign in with your staff account."
    />
  );
}
