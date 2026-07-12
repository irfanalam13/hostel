"use client";

import { WorkspaceLoginForm } from "@/features/auth/components/WorkspaceLoginForm";

/** Admin dashboard login — owner and hostel-admin roles only. */
export default function AdminLoginPage() {
  return (
    <WorkspaceLoginForm
      portal="admin"
      title="Admin Login"
      subtitle="Sign in to manage your hostel."
      showSignup
    />
  );
}
