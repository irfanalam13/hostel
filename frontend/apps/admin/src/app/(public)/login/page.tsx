"use client";

import { Suspense } from "react";
import { WorkspaceLoginForm } from "@/features/auth/components/WorkspaceLoginForm";

/**
 * Unified tenant login — the single sign-in surface for a workspace.
 *
 * Every role authenticates here (owner, hostel admin, staff, receptionist,
 * accountant, warden, parent, student, security, laundry, maintenance …):
 * authentication establishes identity, and the backend routes each role to its
 * own dashboard via the login response's `redirect`. There are no role-specific
 * login pages any more — `/admin`, `/staff-login`, `/student` and `/parent`
 * redirect here for backward compatibility.
 *
 * Workspace-aware: on a workspace host it shows that hostel's branding and
 * needs no Hostel ID; on the root domain the legacy Hostel-ID flow still works.
 */
export default function LoginPage() {
  return (
    <Suspense fallback={<main className="min-h-screen" />}>
      <WorkspaceLoginForm
        title="Sign in"
        subtitle="Sign in to your workspace."
        showSignup
      />
    </Suspense>
  );
}
