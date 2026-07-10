"use client";

import { WorkspaceLoginForm } from "@/features/auth/components/WorkspaceLoginForm";

/**
 * Staff / employee login (also accepts owner/admin accounts — admins may use
 * the staff door, never the reverse). Workspace-aware: on a workspace host it
 * shows that hostel's branding and needs no Hostel ID.
 */
export default function LoginPage() {
  return (
    <WorkspaceLoginForm
      portal="staff"
      title="Staff Login"
      subtitle="Sign in with your staff account."
      showSignup
    />
  );
}
