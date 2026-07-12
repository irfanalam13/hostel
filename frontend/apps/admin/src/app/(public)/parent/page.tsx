"use client";

import { WorkspaceLoginForm } from "@/features/auth/components/WorkspaceLoginForm";

/** Parent portal login — parent/guardian accounts only. */
export default function ParentLoginPage() {
  return (
    <WorkspaceLoginForm
      portal="parent"
      title="Parent Portal"
      subtitle="Sign in to follow your child's stay, payments and notices."
    />
  );
}
